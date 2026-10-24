#!/usr/bin/env python3
"""Tests of check_integrations.py: python3 scripts/check_integrations_test.py (needs PyYAML)"""
import pathlib
import shutil
import sys
import tempfile
import unittest

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_integrations as ci  # noqa: E402

MANIFEST = {
    "id": "redis",
    "name": "Redis",
    "category": "database",
    "description": "Memory, clients, commands and keys of each Redis.",
    "signals": ["metrics"],
    "check": {"datasource": "mimir", "query": "group(max_over_time(redis_up[1h]))"},
    "install": "alloy",
    "settings": [{"name": "REDIS_ADDRESS", "description": "Where Redis listens.", "example": "localhost:6379"}],
}

SNIPPET = """prometheus.exporter.redis "redis" {
  redis_addr = "${REDIS_ADDRESS}"
}

prometheus.remote_write "redis" {
  endpoint {
    url = "${INGEST_URL}/mimir/api/v1/push"
    basic_auth {
      username = "${USERNAME}"
      password = sys.env("TELOPI_PASSWORD")
    }
  }
}
"""

README = "# Redis\n\n## What it collects\n\nx\n\n## What you need\n\nx\n\n## Source and licence\n\nx\n"


class Catalog(unittest.TestCase):
    """A repository of its own, with one integration in it, for each test."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        (self.root / "redis").mkdir()
        (self.root / "redis" / "redis.json").write_text('{"uid": "telopi-redis", "title": "Redis", "panels": []}')
        (self.root / "alerts" / "redis").mkdir(parents=True)
        (self.root / "alerts" / "redis" / "mimir.yaml").write_text("thresholds: {}\ngroups: []\n")
        self.folder = self.root / "integrations" / "redis"
        self.folder.mkdir(parents=True)
        self.write(MANIFEST, SNIPPET, README, ["redis"])

    def write(self, manifest, snippet=None, readme=None, index=None):
        (self.folder / "integration.yaml").write_text(yaml.safe_dump(manifest))
        if snippet is not None:
            (self.folder / "alloy.alloy").write_text(snippet)
        if readme is not None:
            (self.folder / "README.md").write_text(readme)
        if index is not None:
            (self.root / "integrations" / "index.yaml").write_text(yaml.safe_dump(index))

    def problems(self):
        return ci.check(self.root)[0]

    def test_a_good_integration_has_no_problems(self):
        self.assertEqual(self.problems(), [])

    def test_the_index_names_each_folder_once(self):
        self.write(MANIFEST, index=["redis", "redis", "kafka"])
        found = self.problems()
        self.assertIn("integrations/index.yaml: lists redis twice", found)
        self.assertIn("integrations/index.yaml: lists kafka, which has no folder", found)
        self.write(MANIFEST, index=[])
        self.assertIn("integrations/redis/: is not in integrations/index.yaml", self.problems())

    def test_the_manifests_fields(self):
        bad = dict(MANIFEST, id="Redis", category="cache", signals=["metrics", "metrics"], colour="red",
                   check={"datasource": "mimir", "query": "redis_up"})
        self.write(bad)
        found = self.problems()
        rel = "integrations/redis/integration.yaml"
        self.assertIn(f"{rel}: id is its folder's name, redis, in lower-case letters, digits and _", found)
        self.assertTrue(any(f.startswith(f"{rel}: category is one of") for f in found))
        self.assertTrue(any(f.startswith(f"{rel}: signals is") for f in found))
        self.assertIn(f"{rel}: has no key colour", found)
        self.assertTrue(any("[1h]" in f for f in found))

    def test_the_sets_it_names_exist(self):
        self.write(dict(MANIFEST, alerts="alerts/redis/mimir.yaml", dashboards=[{"uid": "telopi-redis", "title": "Redis"}]),
                   readme=README + "\n## Alerts\n\nx\n")
        self.assertEqual(self.problems(), [])
        self.write(dict(MANIFEST, alerts="alerts/redis/loki.yaml", dashboards=[{"uid": "telopi-redis", "title": "Redis!"}]))
        found = self.problems()
        self.assertTrue(any("alerts is a set's file that exists" in f for f in found))
        self.assertTrue(any("is titled 'Redis'" in f for f in found))

    def test_a_dashboards_list_is_its_whole_folder(self):
        (self.root / "redis" / "more.json").write_text('{"uid": "telopi-redis-more", "title": "More", "panels": []}')
        self.write(dict(MANIFEST, dashboards=[{"uid": "telopi-redis", "title": "Redis"}]))
        self.assertIn("integrations/redis/integration.yaml: lists every dashboard of redis/, and not telopi-redis-more",
                      self.problems())

    def test_a_readme_with_alerts_says_what_they_mean(self):
        self.write(dict(MANIFEST, alerts="alerts/redis/mimir.yaml"))
        self.assertIn("integrations/redis/README.md: has a heading ## Alerts", self.problems())

    def test_the_snippets_placeholders_and_environment(self):
        bad = SNIPPET.replace("${REDIS_ADDRESS}", "${REDIS_HOST}").replace('sys.env("TELOPI_PASSWORD")', '"secret"')
        self.write(MANIFEST, snippet=bad)
        found = self.problems()
        rel = "integrations/redis/alloy.alloy"
        self.assertIn(f"{rel}: ${{REDIS_HOST}} is not INGEST_URL, USERNAME or one of its settings", found)
        self.assertIn(f"{rel}: setting REDIS_ADDRESS is used nowhere", found)
        self.assertIn(f'{rel}: reads the password with sys.env("TELOPI_PASSWORD"), never from a placeholder', found)

    def test_a_secret_is_an_env_the_snippet_reads(self):
        snippet = SNIPPET.replace('"${REDIS_ADDRESS}"', '"${REDIS_ADDRESS}"\n  redis_password = sys.env("REDIS_PASSWORD")')
        self.write(MANIFEST, snippet=snippet)
        self.assertIn('integrations/redis/alloy.alloy: sys.env("REDIS_PASSWORD") is not TELOPI_PASSWORD or one of its env',
                      self.problems())
        self.write(dict(MANIFEST, env=[{"name": "REDIS_PASSWORD", "description": "Redis's password."}]))
        self.assertEqual(self.problems(), [])

    def test_every_label_is_the_integrations_own(self):
        self.write(MANIFEST, snippet=SNIPPET.replace('prometheus.remote_write "redis"', 'prometheus.remote_write "default"'))
        self.assertIn('integrations/redis/alloy.alloy: prometheus.remote_write "default" is labelled redis or '
                      'redis_<something>, so snippets can share one Alloy', self.problems())

    def test_telopi_installs_have_no_snippet(self):
        manifest = {k: v for k, v in MANIFEST.items() if k != "settings"}
        self.write(dict(manifest, install="telopi"))
        self.assertIn("integrations/redis/integration.yaml: install is telopi, so it has no alloy.alloy, settings or env",
                      self.problems())
        (self.folder / "alloy.alloy").unlink()
        self.assertEqual(self.problems(), [])

    def test_a_hidden_integration_is_only_an_alert_set(self):
        (self.folder / "alloy.alloy").unlink()
        self.write({"id": "redis", "name": "Redis", "hidden": True, "alerts": "alerts/redis/mimir.yaml"})
        self.assertEqual(self.problems(), [])
        self.write({"id": "redis", "name": "Redis", "hidden": True, "category": "database"})
        self.assertTrue(any("a hidden integration is an alert set with no tile" in f for f in self.problems()))

    def test_render_fills_examples(self):
        out = ci.render(SNIPPET, MANIFEST)
        self.assertIn('"localhost:6379"', out)
        self.assertIn('"https://ingest.telopi.com/example/mimir/api/v1/push"', out)
        self.assertIn('sys.env("TELOPI_PASSWORD")', out)

    def test_the_repository(self):
        self.assertEqual(ci.check(ci.ROOT)[0], [])


if __name__ == "__main__":
    unittest.main()
