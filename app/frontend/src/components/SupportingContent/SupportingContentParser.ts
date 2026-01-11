import DOMPurify from "dompurify";

type ParsedSupportingContentItem = {
    title: string;
    content: string;
    availability?: string;
};

export function parseSupportingContentItem(item: string): ParsedSupportingContentItem {
    // Assumes the item starts with the file name followed by : and the content.
    // Example: "sdp_corporate.pdf: this is the content that follows".
    const parts = item.split(": ");
    const title = parts[0];
    const rawContent = parts.slice(1).join(": ");
    const availabilityMatch = rawContent.match(/Availability:\\s*([0-9.]+)/i);
    let content = rawContent;
    if (availabilityMatch) {
        content = content.replace(availabilityMatch[0], "").replace(/;\\s*\\.?$/, "");
    }
    content = boldMetadataLabels(content);
    const sanitizedContent = DOMPurify.sanitize(content);
    let availability: string | undefined;
    if (availabilityMatch) {
        const parsed = Number(availabilityMatch[1]);
        if (Number.isFinite(parsed)) {
            availability = `${Math.round(parsed * 100)}%`;
        } else {
            availability = availabilityMatch[1];
        }
    }

    return {
        title,
        content: sanitizedContent,
        availability
    };
}

const LABELS_TO_BOLD = [
    "Booking URL",
    "Booking Url",
    "URL",
    "Email",
    "Practice",
    "Pratique",
    "Role",
    "Rôle",
    "Availability",
    "Disponibilité",
    "Location",
    "Localisation",
    "Category",
    "Catégorie",
    "Description",
    "Compétences techniques",
    "Compétences supplémentaires",
    "Compétences additionnelles",
    "Compétences",
    "Competences",
    "Skills",
    "Technologies",
    "Techniques",
    "Méthodes",
    "Methodes",
    "Méthodologies",
    "Methodologies",
    "Outils collaboratifs",
    "Outils et plateformes",
    "Outils et bibliothèques",
    "Outils",
    "Secteur d'activité",
    "Secteurs",
    "Secteur",
    "Domaines de pratique",
    "Domaines",
    "Industry"
];

const labelsByLength = [...LABELS_TO_BOLD].sort((a, b) => b.length - a.length);

function boldMetadataLabels(input: string): string {
    return labelsByLength.reduce((text, label) => {
        const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const pattern = new RegExp(`(^|[\\n\\r\\s;,.])(${escaped})\\s*:`, "gi");
        return text.replace(pattern, (_match, prefix, matched) => `${prefix}**${matched}:**`);
    }, input);
}
