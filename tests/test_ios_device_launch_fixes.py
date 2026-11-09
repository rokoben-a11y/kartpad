"""Pulsar config files, one shader worker, and the iOS surface fill default."""
import importlib.util
import plistlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = (ROOT / "apple/ios/KartPadRuntimeOverlayHost.mm").read_text()
SETTINGS = (ROOT / "apple/third_party/sunpad/SunPadSettings.mm").read_text()
SPEC = importlib.util.spec_from_file_location(
    "limit_ios_pipeline_workers",
    ROOT / "scripts/limit_ios_pipeline_workers.py",
)
PATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCH)

UPSTREAM_WORKERS = """\
static size_t pipeline_worker_count() {
#if defined(__APPLE__) && TARGET_OS_SIMULATOR
  // Avoid an observed Metal Simulator compiler-scheduler crash under parallel submissions.
  return 1;
#endif
  const size_t logicalProcessors = std::thread::hardware_concurrency();
"""


class IosDeviceLaunchFixTests(unittest.TestCase):
    def test_pulsar_config_files_are_real_copies(self) -> None:
        copied = HOST.split("NSSet<NSString *> *copied =", 1)[1].split("];", 1)[0]
        for name in ("ConfigRT.pul", "ConfigCT.pul", "ConfigBT.pul"):
            self.assertIn(name, copied)
        realize = HOST.split("void KartPadRealizePulsarConfigFiles", 1)[1].split(
            "void KartPadProvisionBundledRetroRewind", 1)[0]
        self.assertNotIn("riivolution/save", realize)
        provision = HOST.split("void KartPadProvisionBundledRetroRewind", 1)[1].split(
            "void KartPadProvisionBundledContent", 1)[0]
        marker = provision.split("kKartPadBundledRRMarker", 1)[1]
        self.assertLess(
            marker.index("KartPadRealizePulsarConfigFiles("),
            marker.index("return;"),
        )
        self.assertEqual(provision.count("KartPadRealizePulsarConfigFiles("), 2)
        self.assertIn('kKartPadPinnedRetroRewindVersion = @"6.13.1"', HOST)

    def test_unset_ios_aspect_fills_the_window_surface(self) -> None:
        getter = SETTINGS.split("- (SunPadAspectRatioMode)aspectRatioMode {", 1)[1].split(
            "- (void)setAspectRatioMode:", 1)[0]
        self.assertIn('objectForKey:@"SunPadAspectRatioMode"', getter)
        self.assertIn("#if TARGET_OS_IOS", getter)
        self.assertIn("return SunPadAspectRatioFillScreen;", getter)
        self.assertIn("return SunPadAspectRatioOriginal;", getter)
        host = (ROOT / "apple/ios/KartPadRuntimeOverlayHost.mm").read_text()
        self.assertIn(
            "settings->aspectRatioMode = static_cast<int>(source.aspectRatioMode);",
            host,
        )
        with (ROOT / "apple/ios/RuntimeInfo.plist").open("rb") as handle:
            info = plistlib.load(handle)
        self.assertEqual(info["UILaunchScreen"], {"UIColorName": "LaunchBackground"})
        self.assertNotIn("UILaunchStoryboardName", info)
        self.assertIs(info["UIRequiresFullScreen"], True)
        self.assertEqual(
            info["UISupportedInterfaceOrientations"],
            [
                "UIInterfaceOrientationLandscapeLeft",
                "UIInterfaceOrientationLandscapeRight",
            ],
        )

    def test_device_shader_compile_uses_one_worker_and_stays_aot(self) -> None:
        patched = PATCH.limit_ios_pipeline_workers(UPSTREAM_WORKERS)
        self.assertIn("TARGET_OS_SIMULATOR || TARGET_OS_IOS", patched)
        self.assertEqual(patched, PATCH.limit_ios_pipeline_workers(patched))
        device = (ROOT / "scripts/build-ios-device-game-app.sh").read_text()
        verify = device.index('stage-maintained-runtime.py" --verify')
        limit = device.index("limit_ios_pipeline_workers.py")
        configure = device.index('cmake -S "${runtime_source}"')
        self.assertLess(verify, limit)
        self.assertLess(limit, configure)
        self.assertIn("limit_ios_pipeline_workers.py", (ROOT / "scripts/build-ios-game-app.sh").read_text())
        audit = (ROOT / "scripts/audit-ios-game-app.sh").read_text()
        self.assertIn("JitArm64|JitInterface|CachedInterpreter", audit)
        personal = (ROOT / "scripts/build-personal-device-ipa.sh").read_text()
        self.assertNotIn("KARTPAD_IOS_GAME_PACK_APP=1", personal)


if __name__ == "__main__":
    unittest.main()
