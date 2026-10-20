#!/usr/bin/env python3
"""Checks every dashboard in this repository, as CI does (README, "Checks").

  check.py                    the rules, on the files as they are
  check.py --base origin/main also: no dashboard's uid changed since that ref
  check.py --grafana URL      also: that Grafana (admin:admin) imports each one
"""
import argparse
import base64
import json
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent

# The datasources every Telopi tenant's Grafana has, by uid and type.
DATASOURCES = {"gaas-loki": "loki", "gaas-mimir": "prometheus", "gaas-tempo": "tempo"}
# Grafana's own: annotations, a panel reusing another's query, mixed panels.
BUILT_IN = {"grafana", "-- Grafana --", "-- Dashboard --", "-- Mixed --"}


def datasource_uids(node):
    if isinstance(node, dict):
        ds = node.get("datasource")
        if isinstance(ds, dict) and isinstance(ds.get("uid"), str):
            yield ds["uid"]
        elif isinstance(ds, str):
            yield ds
        for value in node.values():
            yield from datasource_uids(value)
    elif isinstance(node, list):
        for value in node:
            yield from datasource_uids(value)


def git_show(root, ref, rel):
    shown = subprocess.run(["git", "show", f"{ref}:{rel}"], cwd=root, capture_output=True)
    return shown.stdout if shown.returncode == 0 else None


def check(root, base=None):
    """Returns (problems, {path: dashboard}) for every JSON file under root."""
    problems, dashboards, uids = [], {}, {}
    if base and subprocess.run(["git", "rev-parse", "--verify", "--quiet", base], cwd=root, capture_output=True).returncode:
        return [f"--base {base}: no such ref here"], dashboards
    for path in sorted(root.rglob("*.json")):
        rel = path.relative_to(root).as_posix()
        if rel.startswith("."):
            continue
        if rel.count("/") != 1:
            problems.append(f"{rel}: a dashboard goes in its set's folder, <set>/<name>.json")
            continue
        try:
            dashboard = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError) as error:
            problems.append(f"{rel}: not JSON ({error})")
            continue
        if not isinstance(dashboard, dict) or not dashboard.get("title") or not isinstance(dashboard.get("panels"), list):
            problems.append(f"{rel}: not a dashboard: it needs a title and panels")
            continue
        uid = dashboard.get("uid")
        if not isinstance(uid, str) or not 0 < len(uid) <= 40:
            problems.append(f"{rel}: its uid must be a string of 1 to 40 characters")
            continue
        if "__inputs" in dashboard:
            problems.append(f"{rel}: exported for sharing externally; export it again with that off")
        if dashboard.get("id") is not None:
            problems.append(f"{rel}: has an id; remove it, each Grafana numbers its own")
        if uid in uids:
            problems.append(f"{rel}: uid {uid} is also the uid of {uids[uid]}")
        uids[uid] = rel
        for ds in sorted(set(datasource_uids(dashboard))):
            if ds not in DATASOURCES and ds not in BUILT_IN and not ds.startswith("$"):
                problems.append(f"{rel}: datasource {ds!r} is not one every tenant has ({', '.join(DATASOURCES)})")
        old = git_show(root, base, rel) if base else None
        if old is not None:
            try:
                old_uid = json.loads(old).get("uid")
            except ValueError:
                old_uid = None
            if old_uid is not None and old_uid != uid:
                problems.append(f"{rel}: uid changed from {old_uid} to {uid}; links and customers' copies point at the old one")
        dashboards[rel] = dashboard
    if not dashboards and not problems:
        problems.append("no dashboards found")
    return problems, dashboards


def grafana_imports(url, dashboards):
    """Imports each dashboard into a throwaway Grafana that has the tenants' datasources."""
    auth = "Basic " + base64.b64encode(b"admin:admin").decode()

    def call(method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url + path, data=data, method=method,
                                         headers={"Authorization": auth, "Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response)

    for _ in range(60):
        try:
            if call("GET", "/api/health").get("database") == "ok":
                break
        except (OSError, ValueError):
            pass
        time.sleep(2)
    else:
        return [f"{url}: Grafana did not come up"]
    for uid, kind in DATASOURCES.items():
        try:
            call("POST", "/api/datasources", {"name": uid, "uid": uid, "type": kind, "access": "proxy", "url": "http://127.0.0.1:9"})
        except urllib.error.HTTPError as error:
            if error.code != 409:  # already there from an earlier run
                return [f"datasource {uid}: {error.code} {error.read().decode(errors='replace')}"]
    problems = []
    for rel, dashboard in dashboards.items():
        try:
            call("POST", "/api/dashboards/db", {"dashboard": dashboard, "overwrite": True})
        except urllib.error.HTTPError as error:
            problems.append(f"{rel}: Grafana refused it: {error.code} {error.read().decode(errors='replace')}")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", help="a git ref: no dashboard's uid may differ from it")
    parser.add_argument("--grafana", help="a Grafana's URL, with admin:admin, to import each dashboard into")
    args = parser.parse_args()
    problems, dashboards = check(ROOT, args.base)
    if not problems and args.grafana:
        problems = grafana_imports(args.grafana.rstrip("/"), dashboards)
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    print(f"{len(dashboards)} dashboards pass" + (f", and {args.grafana} imports each" if args.grafana else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
