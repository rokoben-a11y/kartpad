#!/usr/bin/env bash
# Copy count-only validation output and the resolved dispatch profile to a
# private directory. Does not copy game data, packs, or IPAs. The public
# workflow must not upload this directory.
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
dest="${KARTPAD_PRIVATE_DIAGNOSTICS_DIR:-}"
if [[ -z "${dest}" ]]; then
  echo "KARTPAD_PRIVATE_DIAGNOSTICS_DIR is unset; private diagnostics were not copied."
  exit 0
fi
if [[ "${dest}" != /* ]]; then
  echo "ERROR: KARTPAD_PRIVATE_DIAGNOSTICS_DIR must be absolute" >&2
  exit 64
fi
case "${dest}" in
  "${repo_root}"/*)
    echo "ERROR: refusing to write diagnostics inside the git repository" >&2
    exit 66
    ;;
esac
mkdir -p "${dest}"
copied=0
while IFS= read -r path; do
  name="$(basename "${path}")"
  case "${name}" in
    kartpad-profile-validation.txt|resolved_dispatch_profile.json|embedded-user-paths.txt) ;;
    *) continue ;;
  esac
  target="${dest}/${name}"
  if [[ -e "${target}" ]]; then
    target="${dest}/$(echo "${path}" | shasum -a 256 | awk '{print substr($1,1,12)}')-${name}"
  fi
  cp -p "${path}" "${target}"
  copied=$((copied + 1))
  if [[ "${name}" == "kartpad-profile-validation.txt" ]]; then
    echo "translation profile validation:"
    cat "${target}"
  else
    echo "retained ${name} ($(wc -c < "${target}") bytes) at ${target}"
  fi
done < <(find "${repo_root}/build/personal-device-ipa" "${repo_root}/private/builder" \
  -type f \( -name kartpad-profile-validation.txt -o -name resolved_dispatch_profile.json \) \
  2>/dev/null || true)
echo "private diagnostics copied: ${copied} file(s) to ${dest}"
