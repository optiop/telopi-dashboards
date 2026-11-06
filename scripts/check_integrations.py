#!/usr/bin/env python3
"""Checks the integrations catalog in integrations/ and the platforms in platforms/, as CI does
(README, "Integrations" and "Platforms").

  check_integrations.py              the manifests, their snippets' placeholders and their READMEs,
                                     and each platform's manifest and steps
  check_integrations.py --alloy CMD  also: Alloy formats and validates each snippet (CMD runs alloy;
                                     {dir} is the snippets' directory, mounted at /snippets)
"""
import argparse
import json
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent

# The portal groups tiles by these, in this order.
CATEGORIES = ["database", "queue", "web_server", "runtime", "infrastructure", "website", "deploys"]
SIGNALS = ["metrics", "logs", "traces"]
DATASOURCES = {"mimir", "loki"}
INSTALLS = {"alloy", "telopi"}
ID = re.compile(r"[a-z][a-z0-9_]*")
NAME = re.compile(r"[A-Z][A-Z0-9_]*")
# What the portal fills in every snippet; the password is never filled.
FILLED = {"INGEST_URL", "USERNAME"}
PASSWORD_ENV = "TELOPI_PASSWORD"
PLACEHOLDER = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")
SYS_ENV = re.compile(r"""sys\.env\(\s*"([^"]*)"\s*\)""")
# A block's header: `prometheus.scrape "label" {`; a nested block has no label.
COMPONENT = re.compile(r'^\s*([a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)+)\s+"([^"]*)"\s*\{', re.M)
# The window a check looks over: an hour, so a tile stays Receiving between scrapes; a
# deploy source may look over a week, since deploys are rare.
WINDOWS = {"deploys": ["[1h]", "[7d]"]}
ALERTS = re.compile(r"alerts/([a-z][a-z0-9_]*)/(mimir|loki)\.yaml")
# What a README says, as these headings; Alerts only where the integration has a set.
README_HEADINGS = ["## What it collects", "## What you need", "## Source and licence"]
VISIBLE_KEYS = {"id", "name", "category", "description", "signals", "check", "install",
                "dashboards", "alerts", "settings", "env"}
REQUIRED_KEYS = {"id", "name", "category", "description", "signals", "check", "install"}
HIDDEN_KEYS = {"id", "name", "hidden", "alerts"}
# What the snippet is validated with: example values where the portal fills them.
EXAMPLE = {"INGEST_URL": "https://ingest.telopi.com/example", "USERNAME": "example"}


def dashboards_by_uid(root):
    """{uid: (folder, title)} of every dashboard in the repository."""
    out = {}
    for path in sorted(root.glob("*/*.json")):
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue  # check.py says so
        if isinstance(d, dict) and isinstance(d.get("uid"), str):
            out[d["uid"]] = (path.parent.name, d.get("title"))
    return out


def named_list(rel, key, value, extra, reserved):
    """Problems of a settings or env list: each {name, description, *extra}, names unique."""
    out, seen = [], set()
    if not isinstance(value, list):
        return [f"{rel}: {key} is a list"]
    for item in value:
        if not isinstance(item, dict) or set(item) != {"name", "description", *extra}:
            out.append(f"{rel}: each of {key} has name, description{''.join(', ' + e for e in extra)} and nothing else")
            continue
        name = item["name"]
        # Every value is checked to be a string before it is hashed or searched: YAML may give a list or a map.
        if not isinstance(name, str) or not NAME.fullmatch(name):
            out.append(f"{rel}: {key} name {name!r} is upper-case letters, digits and _")
        elif name in reserved:
            out.append(f"{rel}: {key} name {name} is Telopi's own")
        elif name in seen:
            out.append(f"{rel}: {key} name {name} is there twice")
        else:
            seen.add(name)
        for field in ("description", *extra):
            if not isinstance(item[field], str) or not item[field].strip():
                out.append(f"{rel}: {key} {name}'s {field} is a string")
            elif field == "example" and any(c in item[field] for c in '"\\\n\r'):
                out.append(f"{rel}: {key} {name}'s example has no double quote, backslash or line break: it goes inside a string")
    return out


def snippet_problems(rel, text, manifest):
    """What is wrong with a snippet's placeholders, environment variables and labels."""
    out = []
    settings = {s["name"] for s in manifest.get("settings") or [] if isinstance(s, dict) and "name" in s}
    env = {e["name"] for e in manifest.get("env") or [] if isinstance(e, dict) and "name" in e}
    used = set(PLACEHOLDER.findall(text))
    out += [f"{rel}: ${{{n}}} is not INGEST_URL, USERNAME or one of its settings" for n in sorted(used - FILLED - settings)]
    out += [f"{rel}: setting {n} is used nowhere" for n in sorted(settings - used)]
    out += [f"{rel}: never uses ${{{n}}}" for n in sorted(FILLED - used)]
    read = set(SYS_ENV.findall(text))
    out += [f"{rel}: sys.env(\"{n}\") is not {PASSWORD_ENV} or one of its env" for n in sorted(read - env - {PASSWORD_ENV})]
    out += [f"{rel}: env {n} is read nowhere" for n in sorted(env - read)]
    if PASSWORD_ENV not in read:
        out.append(f"{rel}: reads the password with sys.env(\"{PASSWORD_ENV}\"), never from a placeholder")
    labels = COMPONENT.findall(text)
    if not labels:
        out.append(f"{rel}: has no component")
    ident = manifest.get("id", "")
    for component, label in labels:
        if label != ident and not label.startswith(ident + "_"):
            out.append(f"{rel}: {component} \"{label}\" is labelled {ident} or {ident}_<something>, so snippets can share one Alloy")
    return out


def render(text, manifest):
    values = dict(EXAMPLE)
    values.update({s["name"]: s["example"] for s in manifest.get("settings") or []})
    return PLACEHOLDER.sub(lambda m: values[m.group(1)], text)


def manifest_problems(rel, doc, folder, files, dashboards, root=ROOT):
    """What is wrong with one integration.yaml; files is the set of names in its folder."""
    if not isinstance(doc, dict):
        return [f"{rel}: is a mapping"]
    out = []
    if doc.get("id") != folder or not ID.fullmatch(folder):
        out.append(f"{rel}: id is its folder's name, {folder}, in lower-case letters, digits and _")
    if not isinstance(doc.get("name"), str) or not 0 < len(doc["name"]) <= 40:
        out.append(f"{rel}: name is a string of 1 to 40 characters")
    alerts = doc.get("alerts")
    if alerts is not None and not (isinstance(alerts, str) and ALERTS.fullmatch(alerts) and (root / alerts).is_file()):
        out.append(f"{rel}: alerts is a set's file that exists, alerts/<set>/<mimir or loki>.yaml")

    if doc.get("hidden") is not None:
        if doc["hidden"] is not True or set(doc) - HIDDEN_KEYS or alerts is None:
            out.append(f"{rel}: a hidden integration is an alert set with no tile: id, name, hidden: true and alerts, nothing else")
        if "alloy.alloy" in files:
            out.append(f"{rel}: a hidden integration has no snippet")
        return out

    out += [f"{rel}: has no key {k}" for k in sorted(set(doc) - VISIBLE_KEYS)]
    out += [f"{rel}: needs {k}" for k in sorted(REQUIRED_KEYS - set(doc))]
    if not isinstance(doc.get("category"), str) or doc["category"] not in CATEGORIES:
        out.append(f"{rel}: category is one of {', '.join(CATEGORIES)}")
    desc = doc.get("description")
    if not isinstance(desc, str) or not 0 < len(desc) <= 160 or "\n" in desc.strip():
        out.append(f"{rel}: description is one line of at most 160 characters")
    signals = doc.get("signals")
    if (not isinstance(signals, list) or not signals or not all(isinstance(x, str) for x in signals)
            or len(set(signals)) != len(signals) or set(signals) - set(SIGNALS)):
        out.append(f"{rel}: signals is a list of some of {', '.join(SIGNALS)}, each once")
    check = doc.get("check")
    if (not isinstance(check, dict) or set(check) != {"datasource", "query"}
            or not isinstance(check["datasource"], str) or check["datasource"] not in DATASOURCES):
        out.append(f"{rel}: check has a datasource (mimir or loki) and a query, and nothing else")
    else:
        windows = WINDOWS.get(doc["category"]) if isinstance(doc.get("category"), str) else None
        if not isinstance(check["query"], str) or not any(w in check["query"] for w in windows or ["[1h]"]):
            out.append(f"{rel}: check's query looks over {' or '.join(windows)}" if windows else
                       f"{rel}: check's query looks over the last hour, [1h], so a tile stays Receiving between scrapes")

    install = doc.get("install")
    if not isinstance(install, str) or install not in INSTALLS:
        out.append(f"{rel}: install is alloy (its snippet is alloy.alloy) or telopi (Telopi does it; the README says how)")
    elif install == "alloy" and "alloy.alloy" not in files:
        out.append(f"{rel}: install is alloy, so its folder has alloy.alloy")
    elif install == "telopi" and ("alloy.alloy" in files or "settings" in doc or "env" in doc):
        out.append(f"{rel}: install is telopi, so it has no alloy.alloy, settings or env")
    out += named_list(rel, "settings", doc["settings"], ["example"], FILLED) if "settings" in doc else []
    out += named_list(rel, "env", doc["env"], [], {PASSWORD_ENV}) if "env" in doc else []

    if "dashboards" in doc:
        listed = doc["dashboards"]
        if not isinstance(listed, list) or not listed or not all(
            isinstance(d, dict) and set(d) == {"uid", "title"} and isinstance(d["uid"], str) and isinstance(d["title"], str) for d in listed
        ):
            out.append(f"{rel}: dashboards is a list of uid and title")
        else:
            folders = set()
            for d in listed:
                if d["uid"] not in dashboards:
                    out.append(f"{rel}: there is no dashboard with uid {d['uid']}")
                    continue
                where, title = dashboards[d["uid"]]
                folders.add(where)
                if d["title"] != title:
                    out.append(f"{rel}: dashboard {d['uid']} is titled {title!r}")
            if len(folders) > 1:
                out.append(f"{rel}: its dashboards are one set, one folder; these are in {', '.join(sorted(folders))}")
            for where in folders:
                missing = sorted(u for u, (f, _) in dashboards.items() if f == where and u not in {d["uid"] for d in listed})
                out += [f"{rel}: lists every dashboard of {where}/, and not {u}" for u in missing]

    if "README.md" not in files:
        out.append(f"{rel}: its folder has a README.md")
    return out


def readme_problems(rel, text, doc):
    headings = README_HEADINGS + (["## Alerts"] if doc.get("alerts") else [])
    lines = {line.strip() for line in text.splitlines()}
    return [f"{rel}: has a heading {h}" for h in headings if h not in lines]


def alloy_problems(rel, text, manifest, alloy):
    """Alloy's own word: alloy fmt parses the snippet as it is, and alloy validate takes it with each placeholder at its example."""
    out = []
    with tempfile.TemporaryDirectory() as d:
        pathlib.Path(d).chmod(0o755)
        for name, body in (("raw.alloy", text), ("rendered.alloy", render(text, manifest))):
            (pathlib.Path(d) / name).write_text(body, encoding="utf-8")
            (pathlib.Path(d) / name).chmod(0o644)
        inside = "/snippets" if "{dir}" in alloy else d
        base = [part.replace("{dir}", d) for part in shlex.split(alloy)]
        fmt = subprocess.run(base + ["fmt", f"{inside}/raw.alloy"], capture_output=True, text=True)
        if fmt.returncode != 0:
            out.append(f"{rel}: alloy fmt: {(fmt.stdout + fmt.stderr).strip()}")
        val = subprocess.run(base + ["validate", f"{inside}/rendered.alloy"], capture_output=True, text=True)
        if val.returncode != 0:
            out.append(f"{rel}: alloy validate, with each placeholder at its example: {(val.stdout + val.stderr).strip()}")
    return out


def check(root, alloy=None):
    """(problems, number of integrations) of the catalog under root."""
    base = root / "integrations"
    index_path = base / "index.yaml"
    if not index_path.is_file():
        return ["integrations/index.yaml: is missing"], 0
    try:
        index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return [f"integrations/index.yaml: not YAML: {e}"], 0
    if not isinstance(index, list) or not all(isinstance(i, str) for i in index):
        return ["integrations/index.yaml: is a list of the integrations' ids"], 0
    out = []
    folders = sorted(p.name for p in base.iterdir() if p.is_dir())
    out += [f"integrations/index.yaml: lists {i} twice" for i in sorted({i for i in index if index.count(i) > 1})]
    out += [f"integrations/index.yaml: lists {i}, which has no folder" for i in index if i not in folders]
    out += [f"integrations/{f}/: is not in integrations/index.yaml" for f in folders if f not in index]

    dashboards = dashboards_by_uid(root)
    claimed = {}
    for ident in [i for i in dict.fromkeys(index) if i in folders]:
        folder = base / ident
        files = {p.name for p in folder.iterdir()}
        rel = f"integrations/{ident}/integration.yaml"
        if "integration.yaml" not in files:
            out.append(f"{rel}: is missing")
            continue
        try:
            doc = yaml.safe_load((folder / "integration.yaml").read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            out.append(f"{rel}: not YAML: {e}")
            continue
        found = manifest_problems(rel, doc, ident, files, dashboards, root)
        out += found
        if found:
            continue
        if doc.get("alerts"):
            if doc["alerts"] in claimed:
                out.append(f"{rel}: alert set {doc['alerts']} is also {claimed[doc['alerts']]}'s")
            claimed[doc["alerts"]] = ident
        if "README.md" in files and not doc.get("hidden"):
            out += readme_problems(f"integrations/{ident}/README.md", (folder / "README.md").read_text(encoding="utf-8"), doc)
        if "alloy.alloy" in files and not doc.get("hidden"):
            text = (folder / "alloy.alloy").read_text(encoding="utf-8")
            snippet_rel = f"integrations/{ident}/alloy.alloy"
            found = snippet_problems(snippet_rel, text, doc)
            out += found
            if alloy and not found:
                out += alloy_problems(snippet_rel, text, doc, alloy)

    # The platform reads alert sets only through the catalog.
    for path in sorted((root / "alerts").glob("*/*.yaml")):
        set_rel = path.relative_to(root).as_posix()
        if set_rel not in claimed:
            out.append(f"{set_rel}: no integration names it, so no customer would get it; add one (hidden: true for a set with no tile)")
    return out, len(index)


# Platforms (Telopi's ADR-0065): where the agent runs, each a tile of the portal's Connect page.
STATUSES = {"ready", "beta", "soon"}
LANGUAGES = {"bash", "yaml", "shell", "text", "alloy"}
PLATFORM_KEYS = {"id", "name", "description", "status", "guide", "collects", "steps"}
STEP_KEYS = {"title", "text", "language", "code"}
# What a step's code may hold: the API fills SNIPPET and INGEST_URL, the portal the rest.
STEP_PLACEHOLDERS = {"INGEST_URL", "USERNAME", "PASSWORD", "ENVIRONMENT", "SNIPPET"}
# What an embedded snippet may hold: what the API and the portal fill, nothing the customer must.
SNIPPET_PLACEHOLDERS = {"INGEST_URL", "USERNAME", "ENVIRONMENT"}
# The password variable set to a value, as VAR=x or VAR: x.
PASSWORD_SET = re.compile(PASSWORD_ENV + r"""\s*[=:]\s*['"]?([^'"\s]*)""")
GUIDE_URL = re.compile(r"""https://[^\s"'<>]+""")
GUIDE_PATH = re.compile(r"[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*")


def guide_problems(rel, guide, root):
    if isinstance(guide, str) and GUIDE_URL.fullmatch(guide):
        return []
    if isinstance(guide, str) and GUIDE_PATH.fullmatch(guide) and ".." not in guide.split("/") and (root / guide).is_file():
        return []
    return [f"{rel}: guide is a file of this repository or an https URL"]


def step_problems(rel, i, step):
    """What is wrong with one step; i counts from 1."""
    at = f"{rel}: step {i}"
    if not isinstance(step, dict) or set(step) != STEP_KEYS:
        return [f"{at} has title, text, language and code, and nothing else"]
    out = [f"{at}'s {k} is a string" for k in sorted(STEP_KEYS) if not isinstance(step[k], str) or not step[k].strip()]
    if out:
        return out
    if step["language"] not in LANGUAGES:
        out.append(f"{at}'s language is one of {', '.join(sorted(LANGUAGES))}")
    out += [f"{at}'s {k} has no placeholder: only code is filled" for k in ("title", "text") if PLACEHOLDER.search(step[k])]
    code = step["code"]
    out += [f"{at}: ${{{n}}} is not one of {', '.join(sorted(STEP_PLACEHOLDERS))}"
            for n in sorted(set(PLACEHOLDER.findall(code)) - STEP_PLACEHOLDERS)]
    for line in code.splitlines():
        if "${SNIPPET}" in line and line != "${SNIPPET}":
            out.append(f"{at}: ${{SNIPPET}} is a line of its own, unindented, so the snippet goes in as it is")
        if "${PASSWORD}" in line and re.search(r"\b(echo|printf)\b", line):
            out.append(f"{at}: never prints the password")
    out += [f"{at}: sets {PASSWORD_ENV} to ${{PASSWORD}}, never to a literal"
            for value in PASSWORD_SET.findall(code) if value != "${PASSWORD}"]
    if re.search(r"""\bpassword\s*=\s*["']""", code):
        out.append(f'{at}: writes no password: Alloy reads sys.env("{PASSWORD_ENV}")')
    return out


def collected_snippets(root):
    """{id: snippet} of the integrations a platform may embed: listed, with a tile, installed by Alloy."""
    base = root / "integrations"
    try:
        index = yaml.safe_load((base / "index.yaml").read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}  # check() says so
    out = {}
    for ident in index if isinstance(index, list) else []:
        try:
            doc = yaml.safe_load((base / str(ident) / "integration.yaml").read_text(encoding="utf-8"))
            text = (base / str(ident) / "alloy.alloy").read_text(encoding="utf-8")
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(doc, dict) and doc.get("install") == "alloy" and not doc.get("hidden"):
            out[ident] = text
    return out


def platform_problems(rel, doc, folder, snippets, root=ROOT):
    """What is wrong with one platform.yaml; snippets is collected_snippets()."""
    if not isinstance(doc, dict):
        return [f"{rel}: is a mapping"]
    out = [f"{rel}: has no key {k}" for k in sorted(set(doc) - PLATFORM_KEYS)]
    out += [f"{rel}: needs {k}" for k in sorted(PLATFORM_KEYS - {"guide"} - set(doc))]
    if doc.get("id") != folder or not ID.fullmatch(folder):
        out.append(f"{rel}: id is its folder's name, {folder}, in lower-case letters, digits and _")
    if not isinstance(doc.get("name"), str) or not 0 < len(doc["name"]) <= 40:
        out.append(f"{rel}: name is a string of 1 to 40 characters")
    desc = doc.get("description")
    if not isinstance(desc, str) or not 0 < len(desc) <= 160 or "\n" in desc.strip():
        out.append(f"{rel}: description is one line of at most 160 characters")
    status = doc.get("status")
    if not isinstance(status, str) or status not in STATUSES:
        out.append(f"{rel}: status is ready, beta or soon")
    if "guide" in doc:
        out += guide_problems(rel, doc["guide"], root)

    collects = doc.get("collects", [])
    if not isinstance(collects, list) or not all(isinstance(c, str) for c in collects) or len(set(collects)) != len(collects):
        out.append(f"{rel}: collects is a list of integrations' ids, each once")
        collects = []
    for c in collects:
        if c not in snippets:
            out.append(f"{rel}: collects {c}, which is no integration with an alloy.alloy")
            continue
        out += [f"{rel}: collects {c}, whose snippet has ${{{n}}}, which nobody fills on Connect"
                for n in sorted(set(PLACEHOLDER.findall(snippets[c])) - SNIPPET_PLACEHOLDERS)]

    steps = doc.get("steps")
    if not isinstance(steps, list):
        return out + [f"{rel}: steps is a list"]
    if status == "soon":
        if steps:
            out.append(f"{rel}: a soon platform has no steps yet")
        if "guide" not in doc:
            out.append(f"{rel}: a soon platform has a guide, where the customer reads how meanwhile")
        return out
    if not steps:
        return out + [f"{rel}: a {status} platform has at least one step"]
    for i, step in enumerate(steps, 1):
        out += step_problems(rel, i, step)
    if not all(isinstance(s, dict) and isinstance(s.get("code"), str) for s in steps):
        return out
    code = "\n".join(s["code"] for s in steps)
    if collects and "${SNIPPET}" not in code:
        out.append(f"{rel}: collects {', '.join(collects)}, so a step writes ${{SNIPPET}}")
    if not collects and "${SNIPPET}" in code:
        out.append(f"{rel}: has ${{SNIPPET}}, so it collects some integration")
    if collects and "${PASSWORD}" not in code:
        out.append(f"{rel}: a step sets {PASSWORD_ENV} from ${{PASSWORD}}, which the snippets read")
    last = steps[-1]
    if not (str(last.get("title")).startswith("Check")
            and ("Receiving data" in str(last.get("text")) or "/api/v1/query" in str(last.get("code")))):
        out.append(f"{rel}: its last step, titled Check ..., says how to tell the data arrived: "
                   "Connect's Receiving data, or a query of the stack")
    return out


def check_platforms(root):
    """(problems, number of platforms) of platforms/ under root; a repository without it has none."""
    base = root / "platforms"
    if not base.is_dir():
        return [], 0
    index_path = base / "index.yaml"
    if not index_path.is_file():
        return ["platforms/index.yaml: is missing"], 0
    try:
        index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return [f"platforms/index.yaml: not YAML: {e}"], 0
    if not isinstance(index, list) or not all(isinstance(i, str) for i in index):
        return ["platforms/index.yaml: is a list of the platforms' ids"], 0
    folders = sorted(p.name for p in base.iterdir() if p.is_dir())
    out = [f"platforms/index.yaml: lists {i} twice" for i in sorted({i for i in index if index.count(i) > 1})]
    out += [f"platforms/index.yaml: lists {i}, which has no folder" for i in index if i not in folders]
    out += [f"platforms/{f}/: is not in platforms/index.yaml" for f in folders if f not in index]
    snippets = collected_snippets(root)
    for ident in [i for i in dict.fromkeys(index) if i in folders]:
        rel = f"platforms/{ident}/platform.yaml"
        path = base / ident / "platform.yaml"
        if not path.is_file():
            out.append(f"{rel}: is missing")
            continue
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            out.append(f"{rel}: not YAML: {e}")
            continue
        out += platform_problems(rel, doc, ident, snippets, root)
    return out, len(index)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--alloy", help="how to run alloy; {dir} is the snippets' directory, mounted at /snippets")
    args = ap.parse_args()
    out, n = check(ROOT, args.alloy)
    platforms, p = check_platforms(ROOT)
    out += platforms
    for line in out:
        print(line)
    print(f"{n} integrations, {p} platforms, {len(out)} problems")
    sys.exit(1 if out else 0)


if __name__ == "__main__":
    main()
