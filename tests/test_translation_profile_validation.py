"""Profile validation must accept the measured 6.13.1 graph and reject the old count."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "builder"))
from kartpad_builder.pipeline import translation_profile_report
PERSONAL = json.loads((ROOT / "builder/personal/mkwii-rmcp01-rev0.json").read_text())
PUBLIC = json.loads((ROOT / "builder/profiles/mkwii-rmcp01-rev0.json").read_text())
CODE_PUL = "7471e1d2f61c11ab0de6544728406ee1359a4eab736b2dc6a73b741f69e7b4a3"


def write_graph(root: Path, generated: int, base: int, retro: int, shards: str = "ON") -> None:
    functions = root / "functions"
    functions.mkdir(parents=True, exist_ok=True)
    for index in range(generated):
        (functions / f"func_{index:08x}.cpp").write_text("int translated() { return 1; }\n")
    cmake = root / "build_shards/shards.cmake"
    cmake.parent.mkdir(parents=True, exist_ok=True)
    cmake.write_text(
        "\n".join([
            f"set(MKW_BASE_FUNCTION_COUNT {base})",
            f"set(MKW_RETRO_REWIND_FUNCTION_COUNT {retro})",
            f"set(MKW_HAVE_RETRO_REWIND_SHARDS {shards})",
            'set(MKW_RETRO_MOD_SHARDS\n  "mod/cpp/secret_game_function.cpp"\n)',
        ]) + "\n"
    )


class TranslationProfileValidationTests(unittest.TestCase):
    def test_personal_6131_pin_matches_the_hosted_graph_and_rejects_neighbors(self) -> None:
        translation = PERSONAL["translation"]
        self.assertEqual(PERSONAL["retroRewind"]["version"], "6.13.1")
        self.assertEqual(PERSONAL["retroRewind"]["codePul"]["sha256"], CODE_PUL)
        self.assertEqual(translation["expectedRetroFunctions"], 4119)
        self.assertEqual(translation["expectedBaseFunctions"], 29064)
        self.assertEqual(translation["expectedGeneratedFunctions"], 29637)
        self.assertEqual(PUBLIC["retroRewind"]["version"], "6.13.5")
        self.assertEqual(PUBLIC["translation"]["expectedRetroFunctions"], 3979)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_graph(root, 3, 29064, 4119)
            passed = translation_profile_report(
                root, 3, translation["expectedBaseFunctions"], translation["expectedRetroFunctions"])
            self.assertEqual(passed, "profile validation passed\n")
            self.assertNotIn("secret_game_function", passed)
            write_graph(root, 3, 29064, 4124)
            failed = translation_profile_report(
                root, 3, translation["expectedBaseFunctions"], translation["expectedRetroFunctions"])
            self.assertIn("profile validation failed", failed)
            self.assertIn("MKW_RETRO_REWIND_FUNCTION_COUNT: actual 4124, expected 4119", failed)
            self.assertNotIn("secret_game_function", failed)
            write_graph(root, 3, 29064, 3979)
            public_count = translation_profile_report(
                root, 3, translation["expectedBaseFunctions"], translation["expectedRetroFunctions"])
            self.assertIn("actual 3979, expected 4119", public_count)
            write_graph(root, 3, 29065, 4119)
            base = translation_profile_report(
                root, 3, translation["expectedBaseFunctions"], translation["expectedRetroFunctions"])
            self.assertIn("MKW_BASE_FUNCTION_COUNT: actual 29065, expected 29064", base)
            report = (root / "kartpad-profile-validation.txt").read_text()
            self.assertEqual(report, base)

    def test_preserve_script_keeps_only_named_diagnostics_outside_the_repo(self) -> None:
        script = ROOT / "scripts/preserve-personal-translation-diagnostics.sh"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = ROOT / "build/personal-device-ipa/mod"
            build.mkdir(parents=True, exist_ok=True)
            profile = build / "resolved_dispatch_profile.json"
            profile.write_text('{"NativeOverriddenModPatches":[]}\n')
            validation = ROOT / "build/personal-device-ipa/translation/kartpad-profile-validation.txt"
            validation.parent.mkdir(parents=True, exist_ok=True)
            validation.write_text("profile validation failed\nMKW_RETRO_REWIND_FUNCTION_COUNT: actual 4119, expected 4124\n")
            packed = build / "Code.pul"
            packed.write_text("not-a-diagnostic")
            inside = root / "inside"
            refused = subprocess.run(
                ["bash", str(script)],
                capture_output=True, text=True, check=False,
                env={"KARTPAD_PRIVATE_DIAGNOSTICS_DIR": str(ROOT / "builder/personal"), "PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(refused.returncode, 66)
            dest = root / "private-diagnostics"
            result = subprocess.run(
                ["bash", str(script)],
                capture_output=True, text=True, check=False,
                env={"KARTPAD_PRIVATE_DIAGNOSTICS_DIR": str(dest), "PATH": "/usr/bin:/bin"},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((dest / "resolved_dispatch_profile.json").is_file())
            self.assertIn("actual 4119, expected 4124", result.stdout)
            self.assertFalse(any(path.name == "Code.pul" for path in dest.iterdir()))
            packed.unlink()
            profile.unlink()
            validation.unlink()
            build.rmdir()
            validation.parent.rmdir()
            (ROOT / "build/personal-device-ipa").rmdir()


if __name__ == "__main__":
    unittest.main()
