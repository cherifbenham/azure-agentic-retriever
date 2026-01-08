#!/bin/sh

. ./scripts/load_python_env.sh

echo 'Running "prepjsonindex.py"'

additionalArgs=""
if [ $# -gt 0 ]; then
  additionalArgs="$@"
fi

./.venv/bin/python ./app/backend/prepjsonindex.py --data ./new-data/index.json --schema ./new-data/index-schema.json $additionalArgs
