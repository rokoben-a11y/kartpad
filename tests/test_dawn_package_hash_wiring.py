"""The runtime must verify the Dawn file it fetches, not the published pin."""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "keep_caller_dawn_package_hash",
    ROOT / "scripts/keep_caller_dawn_package_hash.py",
)
PATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCH)
keep_caller_dawn_package_hash = PATCH.keep_caller_dawn_package_hash
REBUILT = "97fc0231ac406c1ca62bd2937c8b1679aedd48a2f6a6c215b5928518bcc5b0c4"
OFFICIAL = "a361fcca75929fa5c766cfcde979c010a6da7d805e5db8e15c75e73fd8260e78"

# The iphoneos branch as it exists in vendor/runtimes/ios runtime/CMakeLists.txt.
UPSTREAM = """\
set(AURORA_DAWN_PACKAGE_URL "" CACHE STRING "")
    string(TOLOWER "${CMAKE_OSX_SYSROOT}" MKW_APPLE_SYSROOT_LOWER)
    if(CMAKE_SYSTEM_NAME STREQUAL "iOS" AND
       MKW_APPLE_SYSROOT_LOWER MATCHES "iphonesimulator")
        set(AURORA_DAWN_PACKAGE_URL_HASH
            "SHA256=feb5c4e07da90c47d2f279bf83c43bc67db01dac1138cb9af8ea9b5b50c67fbf"
            CACHE STRING "" FORCE)
    elseif(CMAKE_SYSTEM_NAME STREQUAL "iOS")
        set(AURORA_DAWN_PACKAGE_URL_HASH
            "SHA256=a361fcca75929fa5c766cfcde979c010a6da7d805e5db8e15c75e73fd8260e78"
            CACHE STRING "" FORCE)
    else()
        set(AURORA_DAWN_PACKAGE_URL_HASH
            "SHA256=084ffd2ef500d614e443e3d494738272134628867bad3270d67ee8b0fb5f0838"
            CACHE STRING "" FORCE)
    endif()
"""


def run_cmake(body: str, url: str, supplied_hash: str) -> str:
    with tempfile.TemporaryDirectory() as directory:
        script = Path(directory) / "probe.cmake"
        prelude = ""
        if url:
            prelude += f'set(AURORA_DAWN_PACKAGE_URL "{url}")\n'
        if supplied_hash:
            prelude += f'set(AURORA_DAWN_PACKAGE_URL_HASH "{supplied_hash}")\n'
        # Script mode has no cache, so the runtime's non-FORCE URL reset would
        # wipe a -D value. CMake configure does not. Drop that one line here.
        executed = body.replace(
            'set(AURORA_DAWN_PACKAGE_URL "" CACHE STRING "")\n', ""
        )
        script.write_text(
            "set(CMAKE_SYSTEM_NAME iOS)\n"
            "set(CMAKE_OSX_SYSROOT iphoneos)\n"
            + prelude
            + executed
            + "\nmessage(STATUS \"EFFECTIVE_HASH=${AURORA_DAWN_PACKAGE_URL_HASH}\")\n"
        )
        result = subprocess.run(
            ["cmake", "-P", str(script)],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return result.stdout


class DawnPackageHashWiringTests(unittest.TestCase):
    def test_rebuilt_archive_keeps_its_own_digest(self) -> None:
        patched = keep_caller_dawn_package_hash(UPSTREAM)
        self.assertNotEqual(patched, UPSTREAM)
        self.assertEqual(patched, keep_caller_dawn_package_hash(patched))
        url = "file:///tmp/dawn-ios-device-arm64-kartpad.tar.gz"
        supplied = f"SHA256={REBUILT}"
        forced = run_cmake(UPSTREAM, url, supplied)
        kept = run_cmake(patched, url, supplied)
        self.assertIn(f"EFFECTIVE_HASH=SHA256={OFFICIAL}", forced)
        self.assertIn(f"EFFECTIVE_HASH=SHA256={REBUILT}", kept)
        self.assertNotIn(OFFICIAL, kept)
        unpublished = run_cmake(patched, "", "")
        self.assertIn(f"EFFECTIVE_HASH=SHA256={OFFICIAL}", unpublished)

    def test_device_script_patches_the_staged_runtime_before_configure(self) -> None:
        script = (ROOT / "scripts/build-ios-device-game-app.sh").read_text()
        verify = script.index("stage-maintained-runtime.py\" --verify")
        patch = script.index("keep_caller_dawn_package_hash.py")
        configure = script.index("cmake -S \"${runtime_source}\"")
        self.assertLess(verify, patch)
        self.assertLess(patch, configure)
        self.assertIn('AURORA_DAWN_PACKAGE_URL_HASH="SHA256=${dawn_sha256}"', script)


if __name__ == "__main__":
    unittest.main()
