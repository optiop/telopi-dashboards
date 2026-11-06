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
    "alerts": "alerts/redis/mimir.yaml",
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

README = "# Redis\n\n## What it collects\n\nx\n\n## What you need\n\nx\n\n## Alerts\n\nx\n\n## Source and licence\n\nx\n"


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
        self.write(MANIFEST, readme=README.replace("## Alerts", "## Alerting"))
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

    def test_a_deploy_source_is_a_telopi_install_with_no_sets(self):
        (self.folder / "alloy.alloy").unlink()
        (self.root / "alerts" / "redis" / "mimir.yaml").unlink()
        self.write({"id": "redis", "name": "Redis", "category": "deploys", "description": "Deploys.", "signals": ["logs"],
                    "check": {"datasource": "loki", "query": 'sum(count_over_time({service_name="telopi-deploys"}[7d]))'},
                    "install": "telopi"}, readme=README.replace("## Alerts\n\nx\n\n", ""))
        self.assertEqual(self.problems(), [])

    def test_only_a_deploy_source_looks_over_a_week(self):
        self.write(dict(MANIFEST, check={"datasource": "mimir", "query": "group(max_over_time(redis_up[7d]))"}))
        self.assertTrue(any("[1h]" in f for f in self.problems()))
        self.write(dict(MANIFEST, category="deploys", check={"datasource": "mimir", "query": "group(max_over_time(redis_up[30d]))"}))
        self.assertIn("integrations/redis/integration.yaml: check's query looks over [1h] or [7d]", self.problems())

    def test_a_hidden_integration_is_only_an_alert_set(self):
        (self.folder / "alloy.alloy").unlink()
        self.write({"id": "redis", "name": "Redis", "hidden": True, "alerts": "alerts/redis/mimir.yaml"})
        self.assertEqual(self.problems(), [])
        self.write({"id": "redis", "name": "Redis", "hidden": True, "category": "database"})
        self.assertTrue(any("a hidden integration is an alert set with no tile" in f for f in self.problems()))

    def test_a_list_or_a_map_where_a_string_goes_is_a_problem_not_a_traceback(self):
        for key, value in [("category", ["database"]), ("install", {"alloy": 1}), ("signals", [["metrics"]]),
                           ("check", {"datasource": ["mimir"], "query": "x[1h]"}),
                           ("dashboards", [{"uid": ["telopi-redis"], "title": "Redis"}]),
                           ("settings", [{"name": ["REDIS_ADDRESS"], "description": "x", "example": "y"}])]:
            with self.subTest(key=key):
                self.write(dict(MANIFEST, **{key: value}))
                self.assertTrue(self.problems())

    def test_an_example_has_no_backslash_or_line_break(self):
        for example in ["C:\\redis", "localhost\n:6379"]:
            with self.subTest(example=example):
                self.write(dict(MANIFEST, settings=[{"name": "REDIS_ADDRESS", "description": "Where.", "example": example}]))
                self.assertIn("integrations/redis/integration.yaml: settings REDIS_ADDRESS's example has no double quote, "
                              "backslash or line break: it goes inside a string", self.problems())

    def test_every_alert_set_is_some_integrations(self):
        (self.root / "alerts" / "kafka").mkdir()
        (self.root / "alerts" / "kafka" / "mimir.yaml").write_text("thresholds: {}\ngroups: []\n")
        self.write(dict(MANIFEST, alerts="alerts/redis/mimir.yaml"), readme=README + "\n## Alerts\n\nx\n")
        self.assertEqual(self.problems(), ["alerts/kafka/mimir.yaml: no integration names it, so no customer would get it; "
                                           "add one (hidden: true for a set with no tile)"])

    def test_render_fills_examples(self):
        out = ci.render(SNIPPET, MANIFEST)
        self.assertIn('"localhost:6379"', out)
        self.assertIn('"https://ingest.telopi.com/example/mimir/api/v1/push"', out)
        self.assertIn('sys.env("TELOPI_PASSWORD")', out)

    def test_the_repository(self):
        self.assertEqual(ci.check(ci.ROOT)[0], [])


PLATFORM = {
    "id": "linux",
    "name": "Linux",
    "description": "Any Linux machine.",
    "status": "ready",
    "guide": "integrations/redis/README.md",
    "collects": ["redis"],
    "steps": [
        {"title": "Install", "text": "Run it.", "language": "bash",
         "code": "cat > /etc/alloy/config.alloy <<'ALLOY'\n${SNIPPET}\nALLOY\ncat > /etc/default/alloy <<'ENV'\nTELOPI_PASSWORD='${PASSWORD}'\nENV\n"},
        {"title": "Check that it arrived", "text": "Connect says Receiving data.", "language": "bash",
         "code": "systemctl is-active alloy\n"},
    ],
}
SOON = {"id": "linux", "name": "Linux", "description": "Soon.", "status": "soon",
        "guide": "https://grafana.com/docs/alloy/latest/", "collects": [], "steps": []}


class Platforms(unittest.TestCase):
    """Catalog's repository, its redis snippet without a setting, and one platform, linux, that collects it."""

    write = Catalog.write

    def setUp(self):
        Catalog.setUp(self)
        self.write({k: v for k, v in MANIFEST.items() if k != "settings"}, SNIPPET.replace('\n  redis_addr = "${REDIS_ADDRESS}"', ""))
        self.platform = self.root / "platforms" / "linux"
        self.platform.mkdir(parents=True)
        self.place(PLATFORM, ["linux"])

    def place(self, platform, index=None):
        (self.platform / "platform.yaml").write_text(yaml.safe_dump(platform))
        if index is not None:
            (self.root / "platforms" / "index.yaml").write_text(yaml.safe_dump(index))

    def problems(self):
        return ci.check_platforms(self.root)[0]

    def step(self, **change):
        steps = [dict(PLATFORM["steps"][0], **change), PLATFORM["steps"][1]]
        self.place(dict(PLATFORM, steps=steps))
        return self.problems()

    def test_a_good_platform_has_no_problems(self):
        self.assertEqual(self.problems(), [])
        self.place(SOON)
        self.assertEqual(self.problems(), [])

    def test_a_repository_without_platforms_has_none(self):
        shutil.rmtree(self.root / "platforms")
        self.assertEqual(ci.check_platforms(self.root), ([], 0))

    def test_the_index_names_each_folder_once(self):
        self.place(PLATFORM, ["linux", "linux", "macos"])
        found = self.problems()
        self.assertIn("platforms/index.yaml: lists linux twice", found)
        self.assertIn("platforms/index.yaml: lists macos, which has no folder", found)
        self.place(PLATFORM, [])
        self.assertIn("platforms/linux/: is not in platforms/index.yaml", self.problems())

    def test_the_manifests_fields(self):
        self.place(dict(PLATFORM, id="Linux", name="L" * 41, status="done", colour="red", guide="../secrets"))
        rel = "platforms/linux/platform.yaml"
        found = self.problems()
        for want in [f"{rel}: id is its folder's name, linux, in lower-case letters, digits and _",
                     f"{rel}: name is a string of 1 to 40 characters", f"{rel}: status is ready, beta or soon",
                     f"{rel}: has no key colour", f"{rel}: guide is a file of this repository or an https URL"]:
            self.assertIn(want, found)
        self.place(dict(PLATFORM, guide="http://example.com"))
        self.assertIn(f"{rel}: guide is a file of this repository or an https URL", self.problems())

    def test_soon_has_a_guide_and_no_steps(self):
        rel = "platforms/linux/platform.yaml"
        self.place(dict(SOON, steps=PLATFORM["steps"]))
        self.assertIn(f"{rel}: a soon platform has no steps yet", self.problems())
        self.place({k: v for k, v in SOON.items() if k != "guide"})
        self.assertIn(f"{rel}: a soon platform has a guide, where the customer reads how meanwhile", self.problems())
        self.place(dict(PLATFORM, steps=[]))
        self.assertIn(f"{rel}: a ready platform has at least one step", self.problems())

    def test_the_last_step_says_whether_it_arrived(self):
        self.place(dict(PLATFORM, steps=PLATFORM["steps"][:1]))
        self.assertTrue(any("its last step, titled Check" in f for f in self.problems()))
        query = dict(PLATFORM["steps"][1], text="Ask the stack.", code="curl ${INGEST_URL}/mimir/prometheus/api/v1/query\n")
        self.place(dict(PLATFORM, steps=[PLATFORM["steps"][0], query]))
        self.assertEqual(self.problems(), [])

    def test_only_the_placeholders_connect_fills(self):
        found = self.step(code=PLATFORM["steps"][0]["code"] + "x=${HOME}\n", text="Put in ${PASSWORD}.")
        self.assertIn("platforms/linux/platform.yaml: step 1: ${HOME} is not one of ENVIRONMENT, INGEST_URL, PASSWORD, "
                      "SNIPPET, USERNAME", found)
        self.assertIn("platforms/linux/platform.yaml: step 1's text has no placeholder: only code is filled", found)

    def test_the_snippet_is_a_line_of_its_own(self):
        found = self.step(code=PLATFORM["steps"][0]["code"].replace("\n${SNIPPET}", "\n  ${SNIPPET}"))
        self.assertIn("platforms/linux/platform.yaml: step 1: ${SNIPPET} is a line of its own, unindented, so the "
                      "snippet goes in as it is", found)

    def test_collects_names_an_alloy_integration_whose_placeholders_connect_fills(self):
        rel = "platforms/linux/platform.yaml"
        self.place(dict(PLATFORM, collects=["redis", "kafka"]))
        self.assertIn(f"{rel}: collects kafka, which is no integration with an alloy.alloy", self.problems())
        self.write(MANIFEST, SNIPPET)  # its setting, which only the Integrations page asks for
        self.assertIn(f"{rel}: collects redis, whose snippet has ${{REDIS_ADDRESS}}, which nobody fills on Connect", self.problems())
        self.write({k: v for k, v in MANIFEST.items() if k != "settings"}, SNIPPET.replace('\n  redis_addr = "${REDIS_ADDRESS}"', ""))
        self.place(PLATFORM)
        self.place(dict(PLATFORM, collects=[]))
        self.assertIn(f"{rel}: has ${{SNIPPET}}, so it collects some integration", self.problems())

    def test_the_password_is_never_a_literal_nor_printed(self):
        rel = "platforms/linux/platform.yaml"
        found = self.step(code="cat <<'A'\n${SNIPPET}\nA\nTELOPI_PASSWORD=hunter2\necho ${PASSWORD}\n")
        self.assertIn(f"{rel}: step 1: sets TELOPI_PASSWORD to ${{PASSWORD}}, never to a literal", found)
        self.assertIn(f"{rel}: step 1: never prints the password", found)
        found = self.step(code="cat <<'A'\n${SNIPPET}\nA\npassword = \"hunter2\"\n")
        self.assertIn(f'{rel}: step 1: writes no password: Alloy reads sys.env("TELOPI_PASSWORD")', found)
        self.assertIn(f"{rel}: a step sets TELOPI_PASSWORD from ${{PASSWORD}}, which the snippets read", found)

    def test_a_list_or_a_map_where_a_string_goes_is_a_problem_not_a_traceback(self):
        for key, value in [("name", ["Linux"]), ("status", {"ready": 1}), ("collects", [["redis"]]),
                           ("guide", ["x"]), ("steps", [{"title": ["x"], "text": "x", "language": "bash", "code": "x"}]),
                           ("steps", ["x"]), ("steps", "x")]:
            with self.subTest(key=key, value=value):
                self.place(dict(PLATFORM, **{key: value}))
                self.assertTrue(self.problems())

    def test_the_repository(self):
        self.assertEqual(ci.check_platforms(ci.ROOT)[0], [])


if __name__ == "__main__":
    unittest.main()
