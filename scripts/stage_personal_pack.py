#!/usr/bin/env python3
"""Copy packed PAL game data and Retro Rewind 6.13.1 into a newly built app.

Reads the coordinator's private IPA. Writes an unsigned IPA. Does not sign,
and does not copy saves, disc images, or the old executable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path

PIN = "6.13.1"
HOST_MARKERS = (
    b"does not download 6.13.5",
    b".kartpad-bundled-rr-source",
    b"Packed Game Data Missing",
)
FORBIDDEN_NAMES = {"embedded.mobileprovision", "rksys.dat", "_CodeSignature"}
FORBIDDEN_SUFFIXES = {".iso", ".wbfs", ".rvz", ".wia", ".gcz", ".gcm", ".ciso"}
ZIP_TIMESTAMP = (2020, 1, 1, 0, 0, 0)


class StageError(ValueError):
    pass


def require_host_pin(executable: Path) -> None:
    data = executable.read_bytes()
    missing = [marker.decode() for marker in HOST_MARKERS if marker not in data]
    if missing:
        raise StageError(
            "built KartPad executable is missing runtime-host markers "
            + ", ".join(missing)
            + "; KartPadRuntimeOverlayHost.mm was not linked"
        )


def _members(archive: zipfile.ZipFile, suffix: str) -> list[zipfile.ZipInfo]:
    needle = "/" + suffix.strip("/") + "/"
    found = [info for info in archive.infolist()
             if needle in "/" + info.filename and not info.is_dir()]
    if not found:
        names = sorted({name.split("/")[1] for name in archive.namelist()
                        if name.startswith("Payload/") and name.count("/") >= 2})
        raise StageError(
            f"packed source IPA has no {suffix}; Payload entries: {names[:12]}"
        )
    return found


def _safe_relative(filename: str, marker: str) -> str:
    index = filename.find("/" + marker + "/")
    if index < 0:
        raise StageError(f"unexpected packed member: {filename}")
    relative = filename[index + 1:]
    parts = Path(relative).parts
    if relative.startswith("/") or ".." in parts:
        raise StageError(f"unsafe packed member: {filename}")
    return relative


def stage_trees(source_ipa: Path, app: Path) -> dict[str, str]:
    game_root = app / "GameData"
    retro_root = app / "RetroRewind" / "RetroRewind6"
    if game_root.exists() or retro_root.exists():
        raise StageError("app already contains packed GameData or RetroRewind6")
    copied = {"GameData": 0, "RetroRewind/RetroRewind6": 0}
    with zipfile.ZipFile(source_ipa) as archive:
        for marker, count_key in (("GameData", "GameData"),
                                  ("RetroRewind/RetroRewind6", "RetroRewind/RetroRewind6")):
            for info in _members(archive, marker):
                relative = _safe_relative(info.filename, marker)
                if "riivolution/save" in relative:
                    continue
                path = app / relative
                name = path.name
                if name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
                    raise StageError(f"packed tree contains forbidden data: {relative}")
                path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, path.open("wb") as target:
                    while True:
                        block = source.read(1024 * 1024)
                        if not block:
                            break
                        target.write(block)
                copied[count_key] += 1
    version_path = retro_root / "version.txt"
    version = version_path.read_text(encoding="utf-8").strip() if version_path.is_file() else ""
    if version != PIN:
        raise StageError(f"packed Retro Rewind version.txt is {version or 'missing'}, expected {PIN}")
    if not (game_root / "sys" / "fst.bin").is_file():
        raise StageError("packed GameData is missing sys/fst.bin")
    if copied["GameData"] < 1 or copied["RetroRewind/RetroRewind6"] < 1:
        raise StageError(f"packed copy was incomplete: {copied}")
    return {key: str(value) for key, value in copied.items()}


def write_unsigned_ipa(app: Path, output: Path, provenance: dict) -> str:
    if app.name != "KartPad.app":
        raise StageError(f"expected KartPad.app, got {app.name}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".partial")
    if temporary.exists():
        temporary.unlink()
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
        for path in sorted((item for item in app.rglob("*") if item.is_file()), key=lambda item: item.as_posix()):
            relative = path.relative_to(app).as_posix()
            if path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
                raise StageError(f"refusing to package {relative}")
            info = zipfile.ZipInfo(f"Payload/KartPad.app/{relative}", ZIP_TIMESTAMP)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | stat.S_IMODE(path.stat().st_mode)) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            with path.open("rb") as handle, archive.open(info, "w") as target:
                while True:
                    block = handle.read(1024 * 1024)
                    if not block:
                        break
                    target.write(block)
        info = zipfile.ZipInfo("KartPadBuilderProvenance.json", ZIP_TIMESTAMP)
        info.create_system = 3
        info.external_attr = (stat.S_IFREG | 0o644) << 16
        archive.writestr(info, json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    temporary.replace(output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise StageError("unsigned IPA failed its ZIP integrity check")
    return digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ipa", type=Path, required=True)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--output-ipa", type=Path, required=True)
    parser.add_argument("--provenance-out", type=Path)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--ios-runtime", required=True)
    parser.add_argument("--disc-sha256", required=True)
    parser.add_argument("--packed-ipa-sha256", required=True)
    args = parser.parse_args()
    try:
        executable = args.app / "KartPad"
        require_host_pin(executable)
        counts = stage_trees(args.source_ipa, args.app)
        provenance = {
            "schemaVersion": 1,
            "resign": False,
            "bundleIdentifier": "dev.kartpad.app",
            "pinnedRetroRewind": PIN,
            "sourceRevision": args.source_revision,
            "iosRuntime": args.ios_runtime,
            "discImageSha256": args.disc_sha256,
            "packedSourceIpaSha256": args.packed_ipa_sha256,
            "packedFiles": counts,
            "containsUserSuppliedGameData": True,
            "gameCodeRedistributionRights": "not-cleared",
        }
        digest = write_unsigned_ipa(args.app, args.output_ipa, provenance)
        provenance["ipaSha256"] = digest
        if args.provenance_out:
            args.provenance_out.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
        print(digest)
    except (StageError, OSError, zipfile.BadZipFile) as error:
        parser.exit(1, f"ERROR: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
