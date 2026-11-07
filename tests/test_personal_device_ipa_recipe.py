"""The personal IPA recipe builds KartPadDual, not the thin shell, and packs privately."""
import hashlib
import json
import stat
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = (ROOT / "scripts/build-personal-device-ipa.sh").read_text()
PREBUILD = (ROOT / "scripts/prebuild-personal-device-ipa.sh").read_text()
PIPELINE = (ROOT / "builder/kartpad_builder/pipeline.py").read_text()
IOS_RUNTIME = "e47a8a683a24480eb649b1789875960bc2894ef7"


class PersonalDeviceIpaRecipeTests(unittest.TestCase):
    def test_recipe_compiles_the_runtime_host_and_refuses_resign(self) -> None:
        self.assertIn("python3 -m kartpad_builder.cli --profiles-dir", BUILD)
        self.assertIn("build \"${disc}\"", BUILD)
        self.assertIn("scripts/stage_personal_pack.py", BUILD)
        self.assertNotIn("build-ios-shell.sh", BUILD)
        self.assertNotIn("build-ios-device-shell.sh", BUILD)
        self.assertIn("build-ios-device-game-app.sh", PIPELINE)
        self.assertIn('resign must be off', BUILD)
        self.assertIn("/workspace/kp/MarioKart.iso", BUILD)
        self.assertIn(
            "/workspace/Devices/ios-signing/ipas/KartPad-0.8.1-full-offline-unsigned.ipa",
            BUILD,
        )
        pin = subprocess.check_output(
            ["git", "-C", str(ROOT), "ls-files", "-s", "vendor/runtimes/ios"], text=True
        ).split()[1]
        self.assertEqual(pin, IOS_RUNTIME)
        self.assertIn('Xcode ${want}', PREBUILD)
        self.assertIn("builder/personal", PREBUILD)
        self.assertIn("bootstrap --target ios", PREBUILD)
        personal = json.loads((ROOT / "builder/personal/mkwii-rmcp01-rev0.json").read_text())
        public = json.loads((ROOT / "builder/profiles/mkwii-rmcp01-rev0.json").read_text())
        self.assertEqual(personal["retroRewind"]["version"], "6.13.1")
        self.assertEqual(personal["translation"]["expectedRetroFunctions"], 4119)
        self.assertEqual(public["retroRewind"]["version"], "6.13.5")
        self.assertIn("--profiles-dir", BUILD)

    def test_linux_host_stops_before_xcode_or_private_inputs(self) -> None:
        result = subprocess.run(
            ["bash", str(ROOT / "scripts/build-personal-device-ipa.sh"), "/tmp/KartPad-out.ipa"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("arm64 macOS", result.stderr)
        resign = subprocess.run(
            ["bash", str(ROOT / "scripts/prebuild-personal-device-ipa.sh")],
            capture_output=True, text=True, check=False,
            env={"KARTPAD_RESIGN": "on", "PATH": "/usr/bin:/bin"},
        )
        self.assertEqual(resign.returncode, 2)
        self.assertIn("resign must be off", resign.stderr)

    def test_stager_packs_pinned_trees_and_keeps_the_new_executable(self) -> None:
        from scripts.stage_personal_pack import require_host_pin, stage_trees, write_unsigned_ipa
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "KartPad.app"
            app.mkdir()
            executable = app / "KartPad"
            executable.write_bytes(b"NEW-BINARY does not download 6.13.5 .kartpad-bundled-rr-source Packed Game Data Missing")
            executable.chmod(0o755)
            (app / "Info.plist").write_bytes(b"plist")
            source = root / "source.ipa"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("Payload/KartPad.app/KartPad", b"OLD-BINARY")
                archive.writestr("Payload/KartPad.app/GameData/sys/fst.bin", b"fst")
                archive.writestr("Payload/KartPad.app/GameData/sys/boot.bin", b"boot")
                archive.writestr("Payload/KartPad.app/RetroRewind/RetroRewind6/version.txt", "6.13.1\n")
                archive.writestr("Payload/KartPad.app/RetroRewind/RetroRewind6/Binaries/Code.pul", b"code")
                archive.writestr("Payload/KartPad.app/RetroRewind/riivolution/save/rksys.dat", b"save")
            require_host_pin(executable)
            counts = stage_trees(source, app)
            self.assertEqual(counts["GameData"], "2")
            self.assertEqual(counts["RetroRewind/RetroRewind6"], "2")
            self.assertFalse((app / "RetroRewind/riivolution/save/rksys.dat").exists())
            self.assertIn(b"NEW-BINARY", executable.read_bytes())
            output = root / "out.ipa"
            digest = write_unsigned_ipa(app, output, {"resign": False, "pinnedRetroRewind": "6.13.1"})
            self.assertEqual(digest, hashlib.sha256(output.read_bytes()).hexdigest())
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
                self.assertIn("Payload/KartPad.app/GameData/sys/fst.bin", names)
                self.assertIn("Payload/KartPad.app/RetroRewind/RetroRewind6/version.txt", names)
                self.assertNotIn("Payload/KartPad.app/RetroRewind/riivolution/save/rksys.dat", names)
                self.assertIn(b"NEW-BINARY", archive.read("Payload/KartPad.app/KartPad"))
            self.assertEqual(stat.S_IMODE(executable.stat().st_mode) & 0o111, 0o111)


if __name__ == "__main__":
    unittest.main()
