"""Personal v0.8.8 copy: packed data, Retro Rewind 6.13.1 pin, unsigned shell recipe."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "apple/ios/KartPadRuntimeOverlayHost.mm"


class PersonalOfflinePinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = OVERLAY.read_text()

    def test_retro_rewind_stays_on_6_13_1_and_does_not_fetch_6_13_5(self):
        self.assertIn('kKartPadPinnedRetroRewindVersion = @"6.13.1"', self.source)
        self.assertIn("does not download 6.13.5", self.source)
        launch = self.source.split("- (void)completeSelectedMode {", 1)[1].split(
            "- (void)installRetroRewindArchive:", 1)[0]
        self.assertIn("self.retroVersionChecked = YES;", launch)
        self.assertNotIn("[self checkRetroRewindVersionAndContinue];", launch)
        download = self.source.split("- (void)startOfficialRetroRewindDownload {", 1)[1].split(
            "- (void)showRetroRewindOptions {", 1)[0]
        self.assertNotIn("downloadTaskWithURL:", download)
        self.assertNotIn("KartPadRefreshUpdate(", self.source)
        self.assertIn("self.updateButton.hidden = YES;", self.source)

    def test_packed_game_data_does_not_import(self):
        self.assertIn("void KartPadProvisionBundledContent()", self.source)
        self.assertIn('stringByAppendingPathComponent:@"GameData"', self.source)
        self.assertIn("KartPadProvisionBundledContent();", self.source)
        options = self.source.split("- (void)showOptions {", 1)[1].split(
            "- (void)showGamePackRequired {", 1)[0]
        self.assertIn("Packed Game Data Missing", options)
        self.assertNotIn("presentGameDataPicker", options)
        self.assertNotIn("chooseDocumentsRoot", options)
        self.assertIn("Saves stay in KartPad's Application Support folder.", self.source)
        self.assertNotIn('actionWithTitle:@"Import from Extracted Folder…"', self.source)

    def test_unsigned_shell_recipe_is_deterministic(self):
        simulator = (ROOT / "scripts/build-ios-shell.sh").read_text()
        device = (ROOT / "scripts/build-ios-device-shell.sh").read_text()
        for script, sdk, platform in (
            (simulator, "iphonesimulator", "IOSSIMULATOR"),
            (device, "iphoneos", "IOS"),
        ):
            self.assertIn("build directory must be absolute", script)
            self.assertIn("-G Xcode", script)
            self.assertIn(f"-DCMAKE_OSX_SYSROOT={sdk}", script)
            self.assertIn("-DCMAKE_OSX_ARCHITECTURES=arm64", script)
            self.assertIn("-DCMAKE_OSX_DEPLOYMENT_TARGET=16.0", script)
            self.assertIn("CODE_SIGNING_ALLOWED=NO", script)
            self.assertIn("--target KartPad", script)
            self.assertIn("scripts/audit-ios-shell.sh", script)
            self.assertNotIn("codesign", script)
        self.assertIn(" IOS", device)
        self.assertNotIn("iphoneos", simulator)


if __name__ == "__main__":
    unittest.main()
