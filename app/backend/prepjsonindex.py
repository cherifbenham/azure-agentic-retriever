import argparse
import asyncio
import json
import logging
import os
from typing import Any, Optional

import aiohttp
from azure.identity.aio import AzureDeveloperCliCredential
from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    BinaryQuantizationCompression,
    HnswAlgorithmConfiguration,
    HnswParameters,
    MagnitudeScoringFunction,
    MagnitudeScoringParameters,
    RescoringOptions,
    ScoringFunctionAggregation,
    ScoringFunctionInterpolation,
    ScoringProfile,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    VectorSearch,
    VectorSearchCompressionRescoreStorageMethod,
    VectorSearchProfile,
)
from rich.logging import RichHandler

from load_azd_env import load_azd_env
from prepdocslib.embeddings import OpenAIEmbeddings
from prepdocslib.servicesetup import (
    OpenAIHost,
    clean_key_if_exists,
    setup_embeddings_service,
    setup_openai_client,
    setup_search_info,
)

logger = logging.getLogger("scripts")


async def check_search_service_connectivity(search_service: str) -> bool:
    """Check if the search service is accessible by hitting the /ping endpoint."""
    ping_url = f"https://{search_service}.search.windows.net/ping"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ping_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                return response.status == 200
    except Exception as exc:
        logger.debug("Search service ping failed: %s", exc)
        return False


def load_schema(schema_path: str) -> dict[str, Any]:
    with open(schema_path, "r", encoding="utf-8") as schema_file:
        schema = json.load(schema_file)
    if not isinstance(schema, dict):
        raise ValueError("Schema file must contain a JSON object")
    if "fields" not in schema or not isinstance(schema["fields"], list):
        raise ValueError("Schema file must include a fields array")
    return schema


def build_search_fields(field_defs: list[dict[str, Any]]) -> tuple[list[SearchField], dict[str, str]]:
    fields: list[SearchField] = []
    field_types: dict[str, str] = {}
    for field_def in field_defs:
        name = field_def.get("name")
        field_type = field_def.get("type")
        if not name or not field_type:
            raise ValueError("Each field definition must include name and type")
        field_types[name] = field_type
        fields.append(
            SearchField(
                name=name,
                type=field_type,
                key=field_def.get("key", False),
                searchable=field_def.get("searchable", False),
                filterable=field_def.get("filterable", False),
                sortable=field_def.get("sortable", False),
                facetable=field_def.get("facetable", False),
            )
        )
    return fields, field_types


def normalize_value(value: Any, field_type: str) -> Any:
    if value is None:
        return None
    if field_type == "Edm.String":
        if isinstance(value, str):
            return value
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)
    return value


def build_vector_config(
    embeddings: OpenAIEmbeddings, embedding_field_name: str, embedding_dimensions: int
) -> tuple[SearchField, VectorSearch, Optional[AzureOpenAIVectorizer], HnswAlgorithmConfiguration]:
    embedding_field = SearchField(
        name=embedding_field_name,
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        hidden=True,
        searchable=True,
        filterable=False,
        sortable=False,
        facetable=False,
        vector_search_dimensions=embedding_dimensions,
        vector_search_profile_name=f"{embedding_field_name}-profile",
        stored=False,
    )

    text_vectorizer = None
    if embeddings.azure_endpoint and embeddings.azure_deployment_name:
        text_vectorizer = AzureOpenAIVectorizer(
            vectorizer_name=f"{embeddings.open_ai_model_name}-vectorizer",
            parameters=AzureOpenAIVectorizerParameters(
                resource_url=embeddings.azure_endpoint,
                deployment_name=embeddings.azure_deployment_name,
                model_name=embeddings.open_ai_model_name,
            ),
        )

    text_vector_algorithm = HnswAlgorithmConfiguration(
        name="hnsw_config",
        parameters=HnswParameters(metric="cosine"),
    )
    text_vector_compression = BinaryQuantizationCompression(
        compression_name=f"{embedding_field_name}-compression",
        truncation_dimension=1024,
        rescoring_options=RescoringOptions(
            enable_rescoring=True,
            default_oversampling=10,
            rescore_storage_method=VectorSearchCompressionRescoreStorageMethod.PRESERVE_ORIGINALS,
        ),
    )
    text_vector_search_profile = VectorSearchProfile(
        name=f"{embedding_field_name}-profile",
        algorithm_configuration_name=text_vector_algorithm.name,
        compression_name=text_vector_compression.compression_name,
        **({"vectorizer_name": text_vectorizer.vectorizer_name if text_vectorizer else None}),
    )
    vector_search = VectorSearch(
        profiles=[text_vector_search_profile],
        algorithms=[text_vector_algorithm],
        compressions=[text_vector_compression],
        vectorizers=[text_vectorizer] if text_vectorizer else [],
    )

    return embedding_field, vector_search, text_vectorizer, text_vector_algorithm


def build_availability_scoring_profile(field_name: str) -> ScoringProfile:
    return ScoringProfile(
        name="availabilityBoost",
        function_aggregation=ScoringFunctionAggregation.SUM,
        functions=[
            MagnitudeScoringFunction(
                field_name=field_name,
                boost=2.0,
                interpolation=ScoringFunctionInterpolation.LINEAR,
                parameters=MagnitudeScoringParameters(
                    boosting_range_start=0,
                    boosting_range_end=1,
                    should_boost_beyond_range_by_constant=True,
                ),
            )
        ],
    )


async def create_or_update_index(
    search_info,
    schema_fields: list[SearchField],
    embedding_field: SearchField,
    vector_search: VectorSearch,
    vectorizer: Optional[AzureOpenAIVectorizer],
    vector_algorithm: HnswAlgorithmConfiguration,
    availability_scoring_profile: Optional[ScoringProfile] = None,
) -> None:
    index_name = search_info.index_name
    async with search_info.create_search_index_client() as search_index_client:
        index_names = [name async for name in search_index_client.list_index_names()]
        if index_name not in index_names:
            logger.info("Creating new search index %s", index_name)
            index = SearchIndex(
                name=index_name,
                fields=[*schema_fields, embedding_field],
                vector_search=vector_search,
                scoring_profiles=[availability_scoring_profile] if availability_scoring_profile else None,
            )
            await search_index_client.create_index(index)
            return

        logger.info("Search index %s already exists, checking for updates", index_name)
        existing_index = await search_index_client.get_index(index_name)
        update_required = False
        existing_field_names = {field.name for field in existing_index.fields}

        for field in schema_fields:
            if field.name not in existing_field_names:
                existing_index.fields.append(field)
                update_required = True

        if embedding_field.name not in existing_field_names:
            embedding_field.stored = True
            existing_index.fields.append(embedding_field)
            update_required = True

        if availability_scoring_profile:
            existing_profiles = existing_index.scoring_profiles or []
            if not any(profile.name == availability_scoring_profile.name for profile in existing_profiles):
                existing_profiles.append(availability_scoring_profile)
                existing_index.scoring_profiles = existing_profiles
                update_required = True

        if existing_index.vector_search is None:
            existing_index.vector_search = vector_search
            update_required = True
        else:
            vector_search_config = existing_index.vector_search
            if vector_search_config.profiles is None:
                vector_search_config.profiles = []
            if not any(profile.name == vector_search.profiles[0].name for profile in vector_search_config.profiles):
                vector_search_config.profiles.append(vector_search.profiles[0])
                update_required = True

            if vector_search_config.algorithms is None:
                vector_search_config.algorithms = []
            if not any(algorithm.name == vector_algorithm.name for algorithm in vector_search_config.algorithms):
                vector_search_config.algorithms.append(vector_algorithm)
                update_required = True

            if vector_search_config.compressions is None:
                vector_search_config.compressions = []
            if not any(
                compression.compression_name == vector_search.compressions[0].compression_name
                for compression in vector_search_config.compressions
            ):
                vector_search_config.compressions.append(vector_search.compressions[0])
                update_required = True

            if vectorizer:
                if vector_search_config.vectorizers is None:
                    vector_search_config.vectorizers = []
                if not any(
                    existing.vectorizer_name == vectorizer.vectorizer_name
                    for existing in vector_search_config.vectorizers
                ):
                    vector_search_config.vectorizers.append(vectorizer)
                    update_required = True

        if update_required:
            await search_index_client.create_or_update_index(existing_index)


def build_documents(
    records: list[dict[str, Any]],
    field_types: dict[str, str],
    content_field: str,
    embedding_field_name: str,
    embeddings: list[list[float]],
) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    allowed_fields = set(field_types.keys()) | {embedding_field_name}
    for row_index, record in enumerate(records):
        document: dict[str, Any] = {}
        for field_name in allowed_fields:
            if field_name == embedding_field_name:
                continue
            if field_name in record:
                field_type = field_types.get(field_name, "Edm.String")
                value = normalize_value(record[field_name], field_type)
                if value is not None:
                    document[field_name] = value
        if "id" not in document:
            document["id"] = f"row-{row_index}"
        if content_field not in document:
            document[content_field] = ""
        document[embedding_field_name] = embeddings[row_index]
        documents.append(document)
    return documents


async def upload_documents(search_info, documents: list[dict[str, Any]]) -> None:
    max_batch_size = 1000
    async with search_info.create_search_client() as search_client:
        for start in range(0, len(documents), max_batch_size):
            batch = documents[start : start + max_batch_size]
            results = await search_client.upload_documents(batch)
            failed = [result for result in results if not result.succeeded]
            if failed:
                failed_keys = ", ".join(result.key for result in failed)
                raise RuntimeError(f"Failed to upload documents: {failed_keys}")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a JSON-backed search index and upload each JSON row as a record."
    )
    parser.add_argument("--data", default="./new-data/index.json", help="Path to the JSON array file to index")
    parser.add_argument("--schema", default="./new-data/index-schema.json", help="Path to the index schema JSON")
    parser.add_argument("--index", help="Override index name (defaults to schema name)")
    parser.add_argument("--searchservice", help="Override search service (defaults to AZURE_SEARCH_SERVICE)")
    parser.add_argument(
        "--contentfield",
        default="content",
        help="Field to use for embeddings (defaults to content)",
    )
    parser.add_argument(
        "--embeddingfield",
        default=None,
        help="Field name for embeddings (defaults to AZURE_SEARCH_FIELD_NAME_EMBEDDING or embedding)",
    )
    parser.add_argument(
        "--searchkey",
        required=False,
        help="Optional. Use this Azure AI Search account key instead of the current user identity to login",
    )
    parser.add_argument("--disablebatchvectors", action="store_true", help="Disable batch embeddings")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)])
        logger.setLevel(logging.DEBUG)

    load_azd_env()

    search_service = args.searchservice or os.getenv("AZURE_SEARCH_SERVICE") or "gptkb-q3ymwgykjikzi"
    schema = load_schema(args.schema)
    index_name = args.index or schema.get("name") or os.getenv("AZURE_SEARCH_INDEX")
    if not index_name:
        raise ValueError("Index name must be provided via --index, schema name, or AZURE_SEARCH_INDEX")

    content_field = args.contentfield

    schema_field_names = {field.get("name") for field in schema["fields"]}
    if content_field not in schema_field_names:
        raise ValueError(f"Content field '{content_field}' not found in schema fields")

    embedding_field_name = (
        args.embeddingfield or os.getenv("AZURE_SEARCH_FIELD_NAME_EMBEDDING") or "embedding"
    )

    if tenant_id := os.getenv("AZURE_TENANT_ID"):
        logger.info("Connecting to Azure services using the azd credential for tenant %s", tenant_id)
        azd_credential = AzureDeveloperCliCredential(tenant_id=tenant_id, process_timeout=60)
    else:
        logger.info("Connecting to Azure services using the azd credential for home tenant")
        azd_credential = AzureDeveloperCliCredential(process_timeout=60)

    openai_client = None
    try:
        openai_host = OpenAIHost(os.environ["OPENAI_HOST"])
        openai_client, azure_openai_endpoint = setup_openai_client(
            openai_host=openai_host,
            azure_credential=azd_credential,
            azure_openai_service=os.getenv("AZURE_OPENAI_SERVICE"),
            azure_openai_custom_url=os.getenv("AZURE_OPENAI_CUSTOM_URL"),
            azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY_OVERRIDE"),
            openai_api_key=clean_key_if_exists(os.getenv("OPENAI_API_KEY")),
            openai_organization=os.getenv("OPENAI_ORGANIZATION"),
        )

        emb_model_dimensions = 1536
        if os.getenv("AZURE_OPENAI_EMB_DIMENSIONS"):
            emb_model_dimensions = int(os.environ["AZURE_OPENAI_EMB_DIMENSIONS"])

        embeddings_service = setup_embeddings_service(
            openai_host,
            openai_client,
            emb_model_name=os.environ["AZURE_OPENAI_EMB_MODEL_NAME"],
            emb_model_dimensions=emb_model_dimensions,
            azure_openai_deployment=os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT"),
            azure_openai_endpoint=azure_openai_endpoint,
            disable_batch=args.disablebatchvectors,
        )

        search_info = setup_search_info(
            search_service=search_service,
            index_name=index_name,
            azure_credential=azd_credential,
            search_key=clean_key_if_exists(args.searchkey),
        )

        is_connected = await check_search_service_connectivity(search_service)
        if not is_connected:
            raise RuntimeError(f"Unable to connect to search service {search_service}")

        schema_fields, field_types = build_search_fields(schema["fields"])
        if embedding_field_name in field_types:
            logger.info("Replacing schema field %s with vector-enabled field", embedding_field_name)
            schema_fields = [field for field in schema_fields if field.name != embedding_field_name]
            field_types.pop(embedding_field_name, None)
        availability_scoring_profile = None
        if "availability" in field_types:
            availability_scoring_profile = build_availability_scoring_profile("availability")
        embedding_field, vector_search, vectorizer, vector_algorithm = build_vector_config(
            embeddings=embeddings_service,
            embedding_field_name=embedding_field_name,
            embedding_dimensions=embeddings_service.open_ai_dimensions,
        )

        await create_or_update_index(
            search_info=search_info,
            schema_fields=schema_fields,
            embedding_field=embedding_field,
            vector_search=vector_search,
            vectorizer=vectorizer,
            vector_algorithm=vector_algorithm,
            availability_scoring_profile=availability_scoring_profile,
        )

        with open(args.data, "r", encoding="utf-8") as data_file:
            records = json.load(data_file)
        if not isinstance(records, list):
            raise ValueError("Data file must contain a JSON array")
        if not records:
            logger.info("No records found in %s", args.data)
            return
        if not all(isinstance(record, dict) for record in records):
            raise ValueError("Every JSON row must be an object")

        content_texts = [
            normalize_value(record.get(content_field, ""), field_types.get(content_field, "Edm.String")) or ""
            for record in records
        ]
        embeddings = await embeddings_service.create_embeddings(content_texts)

        documents = build_documents(
            records=records,
            field_types=field_types,
            content_field=content_field,
            embedding_field_name=embedding_field_name,
            embeddings=embeddings,
        )
        await upload_documents(search_info, documents)
    finally:
        if openai_client:
            await openai_client.close()
        await azd_credential.close()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
