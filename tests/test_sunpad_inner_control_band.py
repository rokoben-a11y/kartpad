import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "apple/third_party/sunpad/SunPadGameOverlay.mm"
HEADER = ROOT / "apple/third_party/sunpad/SunPadInnerControlBand.h"


class InnerControlBandTests(unittest.TestCase):
    def test_geometry_matches_the_lower_keyboard_region(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "sunpad-inner-control-band-test"
            subprocess.run(
                [
                    "g++", "-std=c++17", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
                    f"-I{HEADER.parent}",
                    str(ROOT / "tests/sunpad_inner_control_band_test.cpp"),
                    "-o", str(binary),
                ],
                check=True,
            )
            subprocess.run([str(binary)], check=True)

    def test_inner_display_uses_size_classes_scene_bounds_and_reserved_regions(self) -> None:
        source = OVERLAY.read_text()
        area = source.split("- (CGRect)touchControlArea {", 1)[1].split(
            "- (void)layoutSubviews {", 1
        )[0]
        self.assertIn("horizontalSizeClass == UIUserInterfaceSizeClassRegular", area)
        self.assertIn("verticalSizeClass == UIUserInterfaceSizeClassRegular", area)
        self.assertIn("SunPadTouchControlArea(", area)
        self.assertIn("self.bounds", area)
        self.assertIn("insets.left, insets.top, insets.right, insets.bottom", area)
        self.assertIn("reservedRegionsOfKind:[UIViewReservedRegionKind divisionRegionKind]", area)
        self.assertIn("reservedRegionsOfKind:[UIViewReservedRegionKind occlusionRegionKind]", area)
        self.assertNotIn("UIScreen", area)
        self.assertNotIn("UIUserInterfaceIdiomPad", area.split("regular x", 1)[0])
        layout = source.split("- (void)layoutSubviews {", 1)[1].split(
            "- (CGFloat)experimentalDPadScale", 1
        )[0]
        self.assertEqual(layout.count("safeArea:safe]"), 11)
        self.assertIn("placeExperimentalDPadGroupWithDefaultFrame:defaultGroupFrame safeArea:safe", layout)
        self.assertIn("[self touchControlArea]", layout)
        self.assertIn("0.7803490991", layout)
        self.assertIn("screenSafe", layout)
        self.assertIn("kSunPadInnerControlBandFraction = 0.40", HEADER.read_text())

    def test_fill_build_and_cover_layout_inputs_stay(self) -> None:
        self.assertEqual(json.loads((ROOT / "version.json").read_text())["build"], 275)
        for plist in ("apple/ios/Info.plist", "apple/ios/RuntimeInfo.plist"):
            self.assertNotIn("UIRequiresFullScreen", (ROOT / plist).read_text())
        settings = (ROOT / "apple/third_party/sunpad/SunPadSettings.mm").read_text()
        self.assertIn("return SunPadAspectRatioFillScreen;", settings)

    def test_bundled_offline_build_opens_the_game(self) -> None:
        host = (ROOT / "apple/ios/KartPadRuntimeOverlayHost.mm").read_text()
        self.assertIn('registerDefaults:@{@"KartPadPreferredGame": @"retro_rewind"}', host)
        mirror = host.split("BOOL KartPadMirrorBundledTree(", 1)[1].split("\n}\n", 1)[0]
        self.assertNotIn("createSymbolicLinkAtPath", mirror)
        self.assertIn('kKartPadBundledRRLayout = @"real-files-v2"', host)
        self.assertIn("[expectedMarker writeToFile:markerPath", host)
        self.assertIn('@"GameData/sys/fst.bin"', host)
        self.assertIn("KartPadProvisionBundledContent();", host)


if __name__ == "__main__":
    unittest.main()
