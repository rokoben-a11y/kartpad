#!/usr/bin/env python3
"""Reject linked archives that embed a builder home path.

Prints only a count. The path list is written to KARTPAD_PRIVATE_DIAGNOSTICS_DIR
when that directory is set.
"""
from __future__ import annotations

import argparse
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "builder"))
from kartpad_builder.packaging import embedded_user_paths, record_embedded_user_paths


def member_bytes(archive: Path, suffix: str) -> bytes:
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            if member.isfile() and member.name.endswith(suffix):
                extracted = bundle.extractfile(member)
                if extracted is None:
                    break
                return extracted.read()
    raise SystemExit(f"ERROR: {archive} has no {suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--tar-member", help="Scan this member of a tar or tar.gz archive")
    args = parser.parse_args()
    if not args.archive.is_file():
        parser.exit(66, f"ERROR: missing archive: {args.archive}\n")
    data = member_bytes(args.archive, args.tar_member) if args.tar_member else args.archive.read_bytes()
    paths = embedded_user_paths(data)
    if not paths:
        print(f"no private user paths: {args.archive.name}")
        return 0
    record_embedded_user_paths(paths)
    parser.exit(
        65,
        f"ERROR: {args.archive.name} embeds {len(paths)} private /Users path(s); "
        "rebuild that dependency with -ffile-prefix-map. "
        "The path list is only in KARTPAD_PRIVATE_DIAGNOSTICS_DIR/embedded-user-paths.txt.\n",
    )


if __name__ == "__main__":
    raise SystemExit(main())
