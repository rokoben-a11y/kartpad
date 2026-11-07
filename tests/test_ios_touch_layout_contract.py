import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "apple/ios/KartPadRuntimeOverlayHost.mm"


class IOSTouchLayoutContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = RUNTIME.read_text()

    def test_seed_does_not_store_a_device_layout(self) -> None:
        seed = self.source.split(
            "void KartPadSeedTouchLayoutDefaults(BOOL force) {", 1
        )[1].split("NSSet<NSString *> *KartPadHiddenTouchControls()", 1)[0]
        self.assertNotIn("UIUserInterfaceIdiomPad", seed)
        self.assertNotIn("NSStringFromCGPoint", seed)
        self.assertIn("pad-control-layout v1", seed)
        apply = self.source.split("- (void)kartPadApplyPolicyTouchLayout {", 1)[1].split(
            "- (void)layoutSubviews {", 1)[0]
        self.assertIn("safeAreaInsets", apply)
        self.assertIn("hp_layout_frames(", apply)
        self.assertIn("saved[binding.identifier] != nil", apply)
        self.assertIn('@"move"', apply)
        self.assertIn('@"A"', apply)
        self.assertIn('@"Start"', apply)

    def test_existing_custom_layouts_and_visibility_are_preserved(self) -> None:
        self.assertIn("KartPadSeedTouchLayoutDefaults(NO);", self.source)
        self.assertIn('if (force || [defaults objectForKey:kKartPadHiddenTouchControlsKey] == nil)', self.source)
        self.assertIn('setObject:@[@"ExperimentalDPad"]', self.source)
        self.assertIn("saved[binding.identifier] != nil", self.source)
        self.assertIn('removeObjectForKey:@"SunPadControlOrigins"', self.source)

    def test_editor_can_hide_and_restore_individual_controls(self) -> None:
        self.assertIn('@"KartPadHiddenTouchControls"', self.source)
        self.assertIn('@"ExperimentalDPad"', self.source)
        self.assertIn('@"Hide selected touch control"', self.source)
        self.assertIn('@"Show selected touch control"', self.source)
        self.assertIn("control.hidden = !editing;", self.source)
        self.assertIn("control.userInteractionEnabled = editing;", self.source)
        self.assertIn("BOOL showing = [hidden containsObject:identifier];", self.source)
        self.assertIn("control.alpha = 1.0;", self.source)

    def test_back_returns_to_touch_settings_and_reset_restores_phone_defaults(self) -> None:
        finish = self.source.split("- (void)kartPadFinishLayoutEditing {", 1)[1].split(
            "- (void)endLayoutEditing {", 1
        )[0]
        self.assertIn("[super finishLayoutEditing];", finish)
        self.assertIn("[self toggleSettingsPanel];", finish)
        self.assertIn('[done setTitle:@"Back"', self.source)
        reset = self.source.split("- (void)resetLayout {", 1)[1].split(
            "- (void)toggleSettingsPanel {", 1
        )[0]
        self.assertIn("[super resetLayout];", reset)
        self.assertIn("removeObjectForKey:kKartPadHiddenTouchControlsKey", reset)
        self.assertIn("KartPadSeedTouchLayoutDefaults(YES);", reset)


if __name__ == "__main__":
    unittest.main()
