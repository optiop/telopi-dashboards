#!/usr/bin/env python3
"""Tests of check_alerts.py: python3 scripts/check_alerts_test.py"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_alerts  # noqa: E402

GOOD = """thresholds:
  down_for:
    default: 3m
    description: How long.
groups:
  - name: uptime
    rules:
      - alert: SiteDown
        expr: probe_success == 0
        for: ${down_for}
        labels:
          severity: critical
        annotations:
          summary: "{{ $labels.instance }} is down"
"""


class CheckAlerts(unittest.TestCase):
    def test_a_good_set_has_no_problems(self):
        self.assertEqual(check_alerts.problems("alerts/uptime/mimir.yaml", GOOD), [])

    def test_render_puts_each_default_in_and_leaves_templates(self):
        groups = check_alerts.rendered_groups(GOOD)
        rule = groups[0]["rules"][0]
        self.assertEqual(rule["for"], "3m")
        self.assertEqual(rule["annotations"]["summary"], "{{ $labels.instance }} is down")

    def test_an_undeclared_or_unused_threshold(self):
        bad = GOOD.replace("${down_for}", "${down_after}")
        found = check_alerts.problems("alerts/uptime/mimir.yaml", bad)
        self.assertIn("alerts/uptime/mimir.yaml: ${down_after} is not one of its thresholds", found)
        self.assertIn("alerts/uptime/mimir.yaml: threshold down_for is used nowhere", found)

    def test_the_rule_shape(self):
        bad = GOOD.replace("severity: critical", "severity: page").replace("summary:", "title:")
        found = check_alerts.problems("alerts/uptime/mimir.yaml", bad)
        self.assertIn("alerts/uptime/mimir.yaml: SiteDown's severity label is critical or warning", found)
        self.assertTrue(any("summary annotation" in f for f in found))

    def test_the_group_is_named_after_its_folder_and_the_file_after_its_ruler(self):
        self.assertIn("alerts/website/mimir.yaml: has one group, named website after its folder",
                      check_alerts.problems("alerts/website/mimir.yaml", GOOD))
        self.assertTrue(check_alerts.problems("alerts/uptime/prometheus.yaml", GOOD))

    def test_a_default_is_a_number_or_a_duration(self):
        bad = GOOD.replace("default: 3m", "default: soon")
        self.assertIn("alerts/uptime/mimir.yaml: threshold down_for's default is a number, or a duration such as 5m",
                      check_alerts.problems("alerts/uptime/mimir.yaml", bad))

    def test_every_set_in_the_repository(self):
        for path in sorted((check_alerts.ROOT / "alerts").glob("*/*.yaml")):
            rel = path.relative_to(check_alerts.ROOT).as_posix()
            self.assertEqual(check_alerts.problems(rel, path.read_text()), [], rel)


if __name__ == "__main__":
    unittest.main()
