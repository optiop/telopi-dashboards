#!/usr/bin/env python3
"""Checks every alert rule set in alerts/, as CI does (README, "Alert rules").

  check_alerts.py                 the rules, with each threshold at its default
  check_alerts.py --promtool CMD  also: promtool parses each Mimir set (CMD runs it)
  check_alerts.py --loki URL      also: that Loki's ruler takes each Loki set
"""
import argparse
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
# Which ruler evaluates a set is its file's name.
RULERS = {"mimir.yaml": "mimir", "loki.yaml": "loki"}
SEVERITIES = {"critical", "warning"}
PLACEHOLDER = re.compile(r"\$\{([a-z][a-z0-9_]*)\}")
DURATION = re.compile(r"[0-9]+(ms|s|m|h|d)")


def render(text, values):
    """text with each ${name} replaced by values[name]; an unknown name is a KeyError."""

    def sub(m):
        return str(values[m.group(1)])

    return PLACEHOLDER.sub(sub, text)


def defaults(doc):
    return {name: t["default"] for name, t in (doc.get("thresholds") or {}).items()}


def problems(rel, text):
    """What is wrong with one set's file, as messages: [] when nothing is."""
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as e:
        return [f"{rel}: not YAML: {e}"]
    if pathlib.PurePosixPath(rel).name not in RULERS:
        return [f"{rel}: a set's file is mimir.yaml or loki.yaml, for the ruler that evaluates it"]
    if not isinstance(doc, dict) or set(doc) != {"thresholds", "groups"}:
        return [f"{rel}: has two keys, thresholds and groups, and no other"]
    out = []
    thresholds = doc["thresholds"] or {}
    for name, t in thresholds.items():
        if not PLACEHOLDER.fullmatch("${" + str(name) + "}"):
            out.append(f"{rel}: threshold {name!r} is named in lower-case letters, digits and _")
        if not isinstance(t, dict) or set(t) != {"default", "description"}:
            out.append(f"{rel}: threshold {name} has a default and a description, and nothing else")
            continue
        d = t["default"]
        if isinstance(d, bool) or not (isinstance(d, (int, float)) or (isinstance(d, str) and DURATION.fullmatch(d))):
            out.append(f"{rel}: threshold {name}'s default is a number, or a duration such as 5m")
    used = set(PLACEHOLDER.findall(text))
    out += [f"{rel}: ${{{n}}} is not one of its thresholds" for n in sorted(used - set(thresholds))]
    out += [f"{rel}: threshold {n} is used nowhere" for n in sorted(set(thresholds) - used)]

    folder = pathlib.PurePosixPath(rel).parent.name
    groups = doc["groups"] or []
    if [g.get("name") for g in groups] != [folder]:
        out.append(f"{rel}: has one group, named {folder} after its folder")
    for g in groups:
        for r in g.get("rules") or []:
            name = r.get("alert")
            if not name:
                out.append(f"{rel}: every rule is an alert; recording rules are the platform's")
                continue
            if (r.get("labels") or {}).get("severity") not in SEVERITIES:
                out.append(f"{rel}: {name}'s severity label is critical or warning")
            if not (r.get("annotations") or {}).get("summary"):
                out.append(f"{rel}: {name} has a summary annotation, which the portal and the mail show")
    return out


def rendered_groups(text):
    doc = yaml.safe_load(text)
    return yaml.safe_load(render(text, defaults(doc)))["groups"]


def promtool_problems(rel, text, promtool):
    with tempfile.TemporaryDirectory() as d:
        path = pathlib.Path(d) / "rules.yaml"
        path.write_text(yaml.safe_dump({"groups": rendered_groups(text)}, sort_keys=False))
        # A promtool in a container mounts {dir} at /rules, and runs as nobody.
        pathlib.Path(d).chmod(0o755)
        path.chmod(0o644)
        inside = "/rules/rules.yaml" if "{dir}" in promtool else str(path)
        cmd = [part.replace("{dir}", d) for part in shlex.split(promtool)] + ["check", "rules", inside]
        res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return [f"{rel}: promtool: {(res.stdout + res.stderr).strip()}"]
    return []


def loki_problems(rel, text, url):
    out = []
    for group in rendered_groups(text):
        body = yaml.safe_dump(group, sort_keys=False).encode()
        req = urllib.request.Request(f"{url}/loki/api/v1/rules/check", data=body, method="POST",
                                     headers={"Content-Type": "application/yaml", "X-Scope-OrgID": "check"})
        try:
            urllib.request.urlopen(req, timeout=10).close()
        except urllib.error.HTTPError as e:
            out.append(f"{rel}: Loki refused group {group['name']}: {e.code} {e.read().decode(errors='replace').strip()}")
            continue
        delete = urllib.request.Request(f"{url}/loki/api/v1/rules/check/{group['name']}", method="DELETE",
                                        headers={"X-Scope-OrgID": "check"})
        urllib.request.urlopen(delete, timeout=10).close()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--promtool", help="how to run promtool; {dir} is the rules' directory, mounted at /rules")
    ap.add_argument("--loki", help="a Loki whose ruler API takes rules for the tenant check")
    args = ap.parse_args()

    files = sorted((ROOT / "alerts").glob("*/*.yaml"))
    if not files:
        sys.exit("no alert rule sets in alerts/")
    out, names = [], {}
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text()
        found = problems(rel, text)
        out += found
        if found:
            continue
        for g in rendered_groups(text):
            for r in g["rules"]:
                if r["alert"] in names:
                    out.append(f"{rel}: alert {r['alert']} is also in {names[r['alert']]}; names are unique")
                names[r["alert"]] = rel
        if args.promtool and path.name == "mimir.yaml":
            out += promtool_problems(rel, text, args.promtool)
        if args.loki and path.name == "loki.yaml":
            out += loki_problems(rel, text, args.loki.rstrip("/"))
    for line in out:
        print(line)
    print(f"{len(files)} rule sets, {len(names)} alerts, {len(out)} problems")
    sys.exit(1 if out else 0)


if __name__ == "__main__":
    main()
