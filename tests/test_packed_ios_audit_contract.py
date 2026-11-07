"""The device audit must match the packed auto-load host, not the import alert."""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
AUDIT = (ROOT / "scripts/audit-ios-game-app.sh").read_text()
HOST = (ROOT / "apple/ios/KartPadRuntimeOverlayHost.mm").read_text()
EXTRACTOR = (ROOT / "apple/ios/KartPadDiscExtractor.mm").read_text()
LINKED = (HOST + "\n" + EXTRACTOR).encode()


def quoted_block(source: str, name: str) -> list[str]:
    start = source.index(f"for {name} in")
    stop = source.index("; do", start)
    return re.findall(r"'([^']*)'|\"([^\"]*)\"", source[start:stop])


def flat(pairs: list[tuple[str, str]]) -> list[str]:
    return [left or right for left, right in pairs]


def present(needle: str) -> bool:
    return any(needle.encode(encoding) in LINKED for encoding in ("utf-8", "utf-16-le", "utf-16-be"))


class PackedIosAuditContractTests(unittest.TestCase):
    def test_device_audit_requires_packed_autoload_and_rejects_the_import_gate(self) -> None:
        required = flat(quoted_block(AUDIT, "packed_contract"))
        absent = flat(quoted_block(AUDIT, "absent_import_gate"))
        self.assertIn("Packed Game Data Missing", required)
        self.assertIn("does not download 6.13.5", required)
        self.assertIn(".kartpad-bundled-rr-source", required)
        self.assertIn("Opening disc image", required)
        self.assertIn("KartPad currently supports RMCP01 (PAL), disc 0, revision 0 only.", required)
        self.assertNotIn("Game Data Required", required)
        self.assertNotIn("Import from Extracted Folder", required)
        self.assertEqual(absent, ["Game Data Required"])
        for needle in required:
            self.assertTrue(present(needle), needle)
        for needle in absent:
            self.assertFalse(present(needle), needle)
        self.assertNotIn('alertControllerWithTitle:@"Game Data Required"', HOST)
        self.assertIn('alertControllerWithTitle:@"Packed Game Data Missing"', HOST)
        self.assertNotIn("game-data importer is not connected", HOST)
        self.assertIn("KARTPAD_IOS_GAME_PACK_APP=1", (ROOT / "scripts/build-ios-app.sh").read_text())
        device = (ROOT / "scripts/build-personal-device-ipa.sh").read_text()
        self.assertIn('--profile mkwii-rmcp01-rev0', device)
        self.assertNotIn("KARTPAD_IOS_GAME_PACK_APP=1", device)


if __name__ == "__main__":
    unittest.main()
