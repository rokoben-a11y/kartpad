#!/usr/bin/env bash
# Public prebuild for the personal unsigned device IPA.
# Fetches pinned source and the physical-iOS Dawn archive. Does not read the
# disc, the packed IPA, or any signing material.
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
case "${KARTPAD_RESIGN:-off}" in
  off|OFF|0|"") ;;
  *) echo "ERROR: resign must be off" >&2; exit 2 ;;
esac
if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "ERROR: personal device IPA prebuild requires arm64 macOS (hosted macos-latest, Xcode 26). This host is $(uname -s) $(uname -m)." >&2
  exit 1
fi

want="${KARTPAD_XCODE:-26}"
selected=""
for candidate in \
  "/Applications/Xcode_${want}.app" \
  "/Applications/Xcode_${want}.0.app" \
  /Applications/Xcode_"${want}"*.app \
  /Applications/Xcode.app
do
  if [[ -d "${candidate}/Contents/Developer" ]]; then
    selected="${candidate}/Contents/Developer"
    break
  fi
done
if [[ -z "${selected}" ]]; then
  echo "ERROR: Xcode ${want} was not found under /Applications" >&2
  exit 66
fi
export DEVELOPER_DIR="${selected}"
version_line="$(xcodebuild -version | awk 'NR==1{print; exit}')"
case "${version_line}" in
  "Xcode ${want}"*) ;;
  *) echo "ERROR: selected ${version_line}; Xcode ${want} is required" >&2; exit 66 ;;
esac
echo "Using ${version_line} at ${DEVELOPER_DIR}"

export PYTHONPATH="${repo_root}/builder${PYTHONPATH:+:${PYTHONPATH}}"
python3 -m kartpad_builder.cli --profiles-dir "${repo_root}/builder/personal" \
  bootstrap --target ios --profile mkwii-rmcp01-rev0
echo "Public iOS device prebuild finished. Disc and packed IPA stay outside the repository."
