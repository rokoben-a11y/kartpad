#!/usr/bin/env python3
"""pad-control-layout v1, version-aligned with projectreach 6e48095.

Geometry is tested on the host. KartPad bindings stay in the app. The policy
does not name a device.
"""
import json
import pathlib
import re
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "apple/shared/control-layout-v1.json"
HEADER = ROOT / "apple/shared/hp_control_layout.h"
BINDINGS = ROOT / "apple/ios/kartpad-control-bindings.json"
VECTORS = ROOT / "tests/fixtures/control-layout-v1-vectors.json"
OVERLAY = ROOT / "apple/ios/KartPadRuntimeOverlayHost.mm"
DUMP = ROOT / "tests/control_layout_dump.c"


def load(path):
    return json.loads(path.read_text())


def boxes_overlap(a, b):
    dx = a[0] - (b[0] + b[2]) if a[0] > b[0] else b[0] - (a[0] + a[2])
    dy = a[1] - (b[1] + b[3]) if a[1] > b[1] else b[1] - (a[1] + a[3])
    return dx < -0.5 and dy < -0.5


def compile_dump():
    out = pathlib.Path(tempfile.mkdtemp(prefix="kartpad-layout-")) / "dump"
    subprocess.run(
        ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-o", str(out), str(DUMP)],
        check=True,
        cwd=ROOT,
    )
    return json.loads(subprocess.check_output([str(out)], cwd=ROOT, text=True))


class ControlLayoutPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.live = compile_dump()
        cls.policy = load(POLICY)
        cls.bindings = load(BINDINGS)
        cls.vectors = load(VECTORS)

    def test_live_dump_matches_vectors(self):
        self.assertEqual(self.live, self.vectors)

    def test_policy_version_matches_the_header(self):
        header = HEADER.read_text()
        self.assertEqual(self.policy["id"], "pad-control-layout")
        self.assertEqual(self.policy["version"], 1)
        self.assertIn(f'#define HP_LAYOUT_POLICY_ID "{self.policy["id"]}"', header)
        self.assertIn(f'#define HP_LAYOUT_POLICY_VERSION {self.policy["version"]}', header)
        self.assertEqual(self.policy["selection"]["large_min_safe_width"], 700)
        self.assertEqual(self.policy["selection"]["large_min_safe_height"], 500)
        self.assertFalse(self.policy["selection"]["uses_device_model"])
        self.assertEqual(self.policy["excluded_consumers"], ["Playport"])
        self.assertIn("KartPad", self.policy["future_consumers"])
        self.assertNotIn("Duo", json.dumps(self.policy))
        self.assertNotRegex(json.dumps(self.policy), r"iPhone\s+\d+")

    def test_kartpad_bindings_use_the_policy_slots(self):
        self.assertEqual(self.bindings["layout_policy"], self.policy["id"])
        self.assertEqual(self.bindings["layout_version"], self.policy["version"])
        self.assertEqual(self.bindings["game"], "kartpad")
        ids = [slot["id"] for slot in self.bindings["slots"]]
        self.assertEqual(ids, [
            "move", "look", "fire", "action", "switch", "zoom",
            "grenade", "melee", "reload", "pause", "flash",
        ])
        for slot_id in ids:
            self.assertIn(slot_id, self.policy["slots"])
        overlay = OVERLAY.read_text()
        rows = re.findall(
            r"\{HP_LAYOUT_([A-Z]+), @\"([^\"]+)\"\}", overlay)
        self.assertEqual(
            [(name.lower(), ident) for name, ident in rows],
            [(slot["id"], slot["kartpad"]) for slot in self.bindings["slots"]
             if slot.get("kind") != "group"],
        )
        self.assertIn("boxes[HP_LAYOUT_FLASH]", overlay)
        self.assertIn('@"ExperimentalDPad"', overlay)
        self.assertIn("safeAreaInsets", overlay)
        self.assertNotIn("UIUserInterfaceIdiomPad", overlay.split(
            "void KartPadSeedTouchLayoutDefaults", 1)[1].split(
            "NSSet<NSString *> *KartPadHiddenTouchControls", 1)[0])

    def test_vectors_cover_both_size_classes_without_a_device_model(self):
        classes = {vector["size_class"] for vector in self.live["vectors"]}
        self.assertEqual(classes, {"compact", "large"})
        by_safe = {(tuple(vector["safe"]), vector["left_handed"]): vector
                   for vector in self.live["vectors"]}
        narrow = by_safe[((47.0, 0.0, 780.0, 340.0), 0)]
        wide = next(vector for vector in self.live["vectors"]
                    if vector["size_class"] == "large" and vector["safe"][2] >= 900)
        self.assertEqual(narrow["size_class"], "compact")
        self.assertLess(self._bottom_gap(narrow), self._bottom_gap(wide))
        mirrored = by_safe[((47.0, 0.0, 780.0, 340.0), 1)]
        self.assertAlmostEqual(
            narrow["frames"][0][0] + narrow["frames"][0][2] / 2
            + mirrored["frames"][0][0] + mirrored["frames"][0][2] / 2,
            47.0 + 47.0 + 780.0, places=3)

    def test_every_vector_stays_inside_and_uncovered(self):
        for vector in self.live["vectors"]:
            sx, sy, sw, sh = vector["safe"]
            frames = vector["frames"]
            self.assertEqual(len(frames), 15)
            for frame in frames:
                self.assertGreaterEqual(frame[0], sx - 0.05)
                self.assertGreaterEqual(frame[1], sy - 0.05)
                self.assertLessEqual(frame[0] + frame[2], sx + sw + 0.05)
                self.assertLessEqual(frame[1] + frame[3], sy + sh + 0.05)
                self.assertGreaterEqual(min(frame[2], frame[3]), 44)
            for i, left in enumerate(frames):
                for right in frames[i + 1:]:
                    self.assertFalse(boxes_overlap(left, right), vector["safe"])
        roomy = self.live["vectors"][0]
        self.assertGreater(roomy["frames"][2][2], roomy["frames"][3][2])

    def _bottom_gap(self, vector):
        _, sy, _, sh = vector["safe"]
        move = vector["frames"][0]
        return (sy + sh) - (move[1] + move[3] / 2)


if __name__ == "__main__":
    unittest.main()
