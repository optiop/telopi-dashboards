"""The rules check.py applies, on a repository made for each test."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from check import check  # noqa: E402


def dashboard(uid, datasource="gaas-mimir", **extra):
    return {"uid": uid, "title": uid, "panels": [{"datasource": {"uid": datasource}, "targets": []}], **extra}


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def write(self, rel, content):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")

    def problems(self, base=None):
        return check(self.root, base)[0]

    def test_a_good_set_passes(self):
        self.write("website/website.json", dashboard("gaas-website", "gaas-loki"))
        self.write("uptime/uptime.json", dashboard("gaas-uptime", "$datasource"))
        self.assertEqual(self.problems(), [])

    def test_each_rule(self):
        cases = {
            "loose.json": (dashboard("a"), "its set's folder"),
            "web/broken.json": ("{", "not JSON"),
            "web/no-panels.json": ({"uid": "b", "title": "b"}, "not a dashboard"),
            "web/no-uid.json": ({"title": "c", "panels": []}, "uid must be"),
            "web/id.json": (dashboard("d", id=7), "has an id"),
            "web/other-ds.json": (dashboard("e", "some-prometheus"), "not one every tenant has"),
            "web/shared.json": (dashboard("f", "${DS_MIMIR}", __inputs=[]), "for sharing externally"),
        }
        for rel, (content, expected) in cases.items():
            with self.subTest(rel=rel):
                self.tearDown()
                self.setUp()
                self.write(rel, content)
                self.assertTrue(any(expected in p for p in self.problems()), self.problems())

    def test_a_uid_is_unique(self):
        self.write("a/one.json", dashboard("same"))
        self.write("b/two.json", dashboard("same"))
        self.assertTrue(any("is also the uid of" in p for p in self.problems()))

    def test_a_uid_never_changes(self):
        git = lambda *args: subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=self.root, check=True, capture_output=True)
        git("init", "-q", "-b", "main")
        self.write("web/site.json", dashboard("old-uid"))
        git("add", ".")
        git("commit", "-qm", "base")
        self.write("web/site.json", dashboard("new-uid"))
        self.assertTrue(any("uid changed from old-uid to new-uid" in p for p in self.problems("main")))
        self.assertTrue(any("no such ref" in p for p in self.problems("nope")))


if __name__ == "__main__":
    unittest.main()
