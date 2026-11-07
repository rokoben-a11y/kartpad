"""Pinned Dawn leaks /Users/runner; packaging must keep rejecting that prefix."""
import io
import plistlib
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "builder"))
from kartpad_builder.packaging import PackageError, audit_app, embedded_user_paths
DAWN_PATH = b"/Users/runner/work/dawn-build/dawn-build/dawn/src/tint/utils/result.h"


def tar_with_member(name: str, payload: bytes) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        info = tarfile.TarInfo(name)
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


class PrivateBuildPathTests(unittest.TestCase):
    def test_dawn_style_file_string_is_a_private_path_and_a_remap_is_not(self) -> None:
        leaked = b"prefix\0" + DAWN_PATH + b"\0suffix"
        self.assertEqual(
            embedded_user_paths(leaked),
            ["/Users/runner/work/dawn-build/dawn-build/dawn/src/tint/utils/result.h"],
        )
        self.assertEqual(embedded_user_paths(b"Dawn/src/tint/utils/result.h\0"), [])

    def test_archive_checker_rejects_the_dawn_builder_path(self) -> None:
        import subprocess
        import sys
        script = ROOT / "scripts/check_private_build_paths.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            leaked = root / "dawn.tar.gz"
            leaked.write_bytes(tar_with_member("lib/libwebgpu_dawn.a", b"\0" + DAWN_PATH + b"\0"))
            clean = root / "clean.tar.gz"
            clean.write_bytes(tar_with_member("lib/libwebgpu_dawn.a", b"Dawn/src/tint/utils/result.h\0"))
            env = {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(ROOT / "builder")}
            rejected = subprocess.run(
                [sys.executable, str(script), "--tar-member", "libwebgpu_dawn.a", str(leaked)],
                capture_output=True, text=True, env=env, check=False,
            )
            self.assertEqual(rejected.returncode, 65, rejected.stderr)
            self.assertIn("1 private /Users path", rejected.stderr)
            self.assertNotIn("result.h", rejected.stderr)
            accepted = subprocess.run(
                [sys.executable, str(script), "--tar-member", "libwebgpu_dawn.a", str(clean)],
                capture_output=True, text=True, env=env, check=False,
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)

    def test_packaging_audit_still_rejects_the_runner_home(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory) / "KartPad.app"
            app.mkdir()
            (app / "Info.plist").write_bytes(plistlib.dumps({"CFBundleExecutable": "KartPad"}))
            (app / "KartPad").write_bytes(b"linked\0" + DAWN_PATH + b"\0")
            with self.assertRaisesRegex(PackageError, "exposes private build path: /Users/runner"):
                audit_app(app, ("/Users/runner",))
            (app / "KartPad").write_bytes(b"Dawn/src/tint/utils/result.h\0")
            audit_app(app, ("/Users/runner",))

    def test_device_build_checks_dawn_and_static_archives(self) -> None:
        device = (ROOT / "scripts/build-ios-device-game-app.sh").read_text()
        prebuild = (ROOT / "scripts/prebuild-personal-device-ipa.sh").read_text()
        dawn = (ROOT / "scripts/build-dawn-ios-device.sh").read_text()
        self.assertIn("check_private_build_paths.py", device)
        self.assertIn("find \"${discio_build}\" -name '*.a'", device)
        self.assertIn("dawn-ios-device-arm64-kartpad.tar.gz", device)
        self.assertIn("scripts/build-dawn-ios-device.sh", prebuild)
        self.assertIn("-ffile-prefix-map=${source_dir}=Dawn", dawn)
        self.assertIn("check_private_build_paths.py", dawn)


if __name__ == "__main__":
    unittest.main()
