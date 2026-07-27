#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_dir="${1:-$project_dir/dist}"
client_dir="$output_dir/client"
build_dir="$(mktemp -d "${TMPDIR:-/tmp}/jufdea-static.XXXXXX")"
trap 'rm -rf "$build_dir"' EXIT

uvx --from "nicegui-pyodide==0.1.1" \
    nicegui-pyodide-build "$build_dir"

# Use content-addressed names for the application files. Static hosts and
# browsers can otherwise keep serving app.py from an earlier deployment even
# though the generated NiceGUI runtime itself has not changed.
build_id="$(
    cd "$project_dir"
    find app.py models.py pdf_utils.py layout.json static GUI -type f -print0 \
        | sort -z \
        | xargs -0 shasum -a 256 \
        | shasum -a 256 \
        | cut -c1-12
)"
app_file="app-$build_id.py"
entrypoint_file="entrypoint-$build_id.py"
config_file="pyscript-$build_id.toml"
archive_file="app-assets-$build_id.zip"
css_file="app-$build_id.css"

cp "$project_dir/app.py" "$build_dir/$app_file"
cp "$project_dir/static/entrypoint.py" "$build_dir/$entrypoint_file"
cp "$project_dir/static/pyscript.toml" "$build_dir/$config_file"
cp "$project_dir/static/app.css" "$build_dir/$css_file"

archive_path="$build_dir/$archive_file"
(
    cd "$project_dir"
    zip -q -r "$archive_path" models.py pdf_utils.py layout.json GUI
)

perl -0pi -e "s#\\./app\\.py#./$app_file#; s#\\./app-assets\\.zip#./$archive_file#" \
    "$build_dir/$config_file"
perl -0pi -e 's#<title>.*?</title>#<title>JufDea Naamkaartjes v2026</title>#' \
    "$build_dir/index.html"
perl -0pi -e "s#</title>#</title>\\n    <link rel=\"stylesheet\" href=\"$css_file\">#" \
    "$build_dir/index.html"
perl -0pi -e 's#<div id="loading">.*?</div>#<div id="loading"><strong>Naamkaartjes worden geladen…</strong><br><span>De eerste keer kan dit even duren.</span></div>#' \
    "$build_dir/index.html"
perl -0pi -e 's!#loading \{ padding: 2em; font-family: sans-serif; color: #666; \}!#loading { min-height: 100vh; display: grid; place-content: center; gap: .4rem; padding: 2rem; text-align: center; font-family: sans-serif; color: #356859; background: #f5f4ef; }!' \
    "$build_dir/index.html"
perl -0pi -e "s#src=\"entrypoint\\.py\" config=\"pyscript\\.toml\"#src=\"$entrypoint_file\" config=\"$config_file\"#" \
    "$build_dir/index.html"

mkdir -p "$output_dir"
rm -rf "$client_dir"
mv "$build_dir" "$client_dir"
trap - EXIT

echo "Static site built in $output_dir (build $build_id)"
