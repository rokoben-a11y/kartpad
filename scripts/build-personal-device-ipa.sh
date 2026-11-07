#!/usr/bin/env bash
# Build the unsigned physical-iOS KartPad app, then pack private game data.
#
# This is the production device path (builder -> build-ios-device-game-app.sh
# -> KartPadDual). vendor/runtimes/ios PublicProducts.cmake compiles
# apple/ios/KartPadRuntimeOverlayHost.mm into that target. The thin
# simulator shell target does not compile that file.
#
# Private inputs stay on the coordinator. They are hashed, never committed.
#   KARTPAD_DISC_IMAGE          default /workspace/kp/MarioKart.iso
#   KARTPAD_PACKED_SOURCE_IPA   default the 0.8.1 full-offline unsigned IPA
#   KARTPAD_OUTPUT_IPA          or pass the IPA path as $1
#   KARTPAD_RESIGN              must be off for this step
#   KARTPAD_PRIVATE_DIAGNOSTICS_DIR
#       absolute directory outside the checkout; on failure and success the
#       count report and resolved_dispatch_profile.json are copied there.
# This step stays unsigned. A successful exit leaves the IPA for the private
# workflow's existing signing and publish steps.
set -euo pipefail

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
preserve_diagnostics() {
  "${repo_root}/scripts/preserve-personal-translation-diagnostics.sh" || true
}
trap preserve_diagnostics EXIT
case "${KARTPAD_RESIGN:-off}" in
  off|OFF|0|"") ;;
  *) echo "ERROR: resign must be off" >&2; exit 2 ;;
esac
if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "ERROR: personal device IPA requires arm64 macOS (hosted macos-latest, Xcode 26). This host is $(uname -s) $(uname -m)." >&2
  exit 1
fi

disc="${KARTPAD_DISC_IMAGE:-/workspace/kp/MarioKart.iso}"
packed="${KARTPAD_PACKED_SOURCE_IPA:-/workspace/Devices/ios-signing/ipas/KartPad-0.8.1-full-offline-unsigned.ipa}"
output="${1:-${KARTPAD_OUTPUT_IPA:-}}"
if [[ -z "${output}" || "${output}" != /* || "${output}" != *.ipa ]]; then
  echo "ERROR: output IPA must be an absolute .ipa path (argument or KARTPAD_OUTPUT_IPA)" >&2
  exit 64
fi
for private_path in "${disc}" "${packed}"; do
  if [[ "${private_path}" != /* || ! -f "${private_path}" ]]; then
    echo "ERROR: missing private input: ${private_path}" >&2
    exit 66
  fi
done
case "${output}" in
  "${repo_root}"/*)
    echo "ERROR: refusing to write the IPA inside the git repository: ${output}" >&2
    exit 66
    ;;
esac

work="${repo_root}/build/personal-device-ipa"
base_ipa="${work}/base-unsigned.ipa"
rm -rf "${work}"
mkdir -p "${work}"

export PYTHONPATH="${repo_root}/builder${PYTHONPATH:+:${PYTHONPATH}}"
python3 -m kartpad_builder.cli --profiles-dir "${repo_root}/builder/personal" \
  build "${disc}" \
  --profile mkwii-rmcp01-rev0 \
  --output "${base_ipa}" \
  --work-root "${work}/builder" \
  --jobs "${KARTPAD_JOBS:-2}"

python3 - "${base_ipa}" "${work}/KartPad.app" <<'PY'
import sys, zipfile
from pathlib import Path
ipa, dest = Path(sys.argv[1]), Path(sys.argv[2])
prefix = "Payload/KartPad.app/"
with zipfile.ZipFile(ipa) as archive:
    names = [name for name in archive.namelist() if name.startswith(prefix) and not name.endswith("/")]
    if not names:
        raise SystemExit("ERROR: builder IPA has no Payload/KartPad.app")
    for name in names:
        target = dest / name[len(prefix):]
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(name) as source, target.open("wb") as handle:
            while True:
                block = source.read(1024 * 1024)
                if not block:
                    break
                handle.write(block)
    executable = dest / "KartPad"
    executable.chmod(0o755)
PY

revision="$(git -C "${repo_root}" rev-parse HEAD)"
runtime="$(git -C "${repo_root}" ls-files -s vendor/runtimes/ios | awk '{print $2}')"
disc_sha="$(shasum -a 256 "${disc}" | awk '{print $1}')"
packed_sha="$(shasum -a 256 "${packed}" | awk '{print $1}')"
python3 "${repo_root}/scripts/stage_personal_pack.py" \
  --source-ipa "${packed}" \
  --app "${work}/KartPad.app" \
  --output-ipa "${output}" \
  --provenance-out "${output%.ipa}.provenance.json" \
  --source-revision "${revision}" \
  --ios-runtime "${runtime}" \
  --disc-sha256 "${disc_sha}" \
  --packed-ipa-sha256 "${packed_sha}"
echo "Unsigned personal IPA: ${output}"
