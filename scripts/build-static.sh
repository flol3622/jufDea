#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_dir="${1:-$project_dir/dist}"
client_dir="$output_dir/client"

uvx --from "nicegui-pyodide==0.1.1" \
    nicegui-pyodide-build "$client_dir"

cp "$project_dir/app.py" "$client_dir/app.py"
cp "$project_dir/static/entrypoint.py" "$client_dir/entrypoint.py"
cp "$project_dir/static/pyscript.toml" "$client_dir/pyscript.toml"

archive_path="$client_dir/app-assets.zip"
(
    cd "$project_dir"
    zip -q -r "$archive_path" models.py pdf_utils.py layout.json GUI
)

perl -0pi -e 's#<title>.*?</title>#<title>JufDea Naamkaartjes v2026</title>#' \
    "$client_dir/index.html"
perl -0pi -e 's#<div id="loading">.*?</div>#<div id="loading"><strong>Naamkaartjes worden geladen…</strong><br><span>De eerste keer kan dit even duren.</span></div>#' \
    "$client_dir/index.html"
perl -0pi -e 's!#loading \{ padding: 2em; font-family: sans-serif; color: #666; \}!#loading { min-height: 100vh; display: grid; place-content: center; gap: .4rem; padding: 2rem; text-align: center; font-family: sans-serif; color: #356859; background: #f5f4ef; }!' \
    "$client_dir/index.html"

echo "Static site built in $output_dir"
