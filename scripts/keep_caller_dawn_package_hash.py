#!/usr/bin/env python3
"""Let a caller-supplied Dawn package keep the hash of that exact file.

runtime/CMakeLists.txt FORCE-sets AURORA_DAWN_PACKAGE_URL_HASH to the
published iphoneos archive after the command line is read. A rebuilt archive
then fails FetchContent: the URL is the new file and the expected hash is
still a361fcca. When the caller already set the URL, leave the caller's hash.
"""
from __future__ import annotations

import sys
from pathlib import Path

OFFICIAL_IOS_HASH = (
    "SHA256=a361fcca75929fa5c766cfcde979c010a6da7d805e5db8e15c75e73fd8260e78"
)
MARKER = 'string(TOLOWER "${CMAKE_OSX_SYSROOT}" MKW_APPLE_SYSROOT_LOWER)'


def keep_caller_dawn_package_hash(text: str) -> str:
    if OFFICIAL_IOS_HASH not in text:
        raise ValueError("runtime Dawn iphoneos hash pin not found")
    marker_at = text.find(MARKER)
    if marker_at < 0:
        raise ValueError("runtime Dawn sysroot hash block not found")
    line_start = text.rfind("\n", 0, marker_at) + 1
    if "if(NOT AURORA_DAWN_PACKAGE_URL)" in text[max(0, line_start - 80):line_start]:
        return text
    end_token = "\n    endif()"
    end_at = text.find(end_token, text.find(OFFICIAL_IOS_HASH, marker_at))
    if end_at < 0:
        raise ValueError("runtime Dawn hash block did not end")
    end = end_at + len(end_token)
    block = text[line_start:end]
    indented = "\n".join(f"    {line}" if line else line for line in block.split("\n"))
    wrapped = "    if(NOT AURORA_DAWN_PACKAGE_URL)\n" + indented + "\n    endif()"
    return text[:line_start] + wrapped + text[end:]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: keep_caller_dawn_package_hash.py /path/to/staged/CMakeLists.txt")
    path = Path(sys.argv[1])
    updated = keep_caller_dawn_package_hash(path.read_text())
    path.write_text(updated)
    print(f"Dawn package hash stays with the caller-supplied URL: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
