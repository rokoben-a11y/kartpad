#!/usr/bin/env python3
"""Keep physical iOS shader compilation on one worker.

pipeline_worker_count() already returns 1 for the Simulator. A device uses
every core except two, up to 22, and each worker calls compile_pending_pipeline
with no allocation handler. Parallel Tint jobs are the path that aborts when
the allocation fails. One worker leaves on-demand compilation in place.
"""
from __future__ import annotations

import sys
from pathlib import Path

OLD = """\
static size_t pipeline_worker_count() {
#if defined(__APPLE__) && TARGET_OS_SIMULATOR
  // Avoid an observed Metal Simulator compiler-scheduler crash under parallel submissions.
  return 1;
#endif
"""

NEW = """\
static size_t pipeline_worker_count() {
#if defined(__APPLE__) && (TARGET_OS_SIMULATOR || TARGET_OS_IOS)
  // Device Tint compiles abort on allocation if several workers run at once.
  // The Simulator Metal scheduler also crashes under parallel submissions.
  return 1;
#endif
"""


def limit_ios_pipeline_workers(text: str) -> str:
    if NEW in text:
        return text
    if OLD not in text:
        raise ValueError("iOS pipeline worker policy was not found")
    return text.replace(OLD, NEW, 1)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: limit_ios_pipeline_workers.py /path/to/staged/aurora-main/lib/gfx/pipeline_cache.cpp"
        )
    path = Path(sys.argv[1])
    updated = limit_ios_pipeline_workers(path.read_text())
    path.write_text(updated)
    print(f"iOS shader compilation uses one worker: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
