# Telopi dashboards

The dashboards every [Telopi](https://telopi.com) customer gets in their own
Grafana. Change one here, and once the change is merged to `main`, every
customer's Grafana shows it.

It is public on purpose: the dashboards hold queries and layout, nothing of a
customer's, and anyone can read them.

## How they reach customers

Each customer's Grafana reads this repository through Grafana's
[Git Sync](https://grafana.com/docs/grafana/latest/as-code/observability-as-code/provision-resources/intro-git-sync/):
one read-only connection per dashboard set the customer has, to `main`, over
plain git, polled every five minutes. Each set is a folder in their Grafana.

- **Read-only.** Grafana refuses to save over or delete a dashboard that comes
  from here. A customer who wants a variant uses *Save as* into a folder of
  their own, and no later change here touches their copy.
- **Every five minutes.** A merge to `main` reaches every customer within five
  minutes, and so does a mistake. Undo one by reverting it; the revert arrives
  the same way.

Not connected yet: customers' Grafanas still get these dashboards from the
platform's own chart, and switch to this repository in the platform's next
data-plane release. Until then, a change here must also be made there.

## The sets

| Folder | Dashboards | A customer has it when |
| --- | --- | --- |
| [`website/`](website) | Website: page loads, sessions, JavaScript errors, Core Web Vitals and where visitors come from, from the browser telemetry their sites send | their sites send browser telemetry |
| [`uptime/`](uptime) | Uptime: which checked sites are up, their availability and response time | Telopi checks their sites |

A new set is a new folder. It reaches customers once the platform knows which
customers have it, so add the folder and the platform's change together.

## Rules for a dashboard

[`scripts/check.py`](scripts/check.py) checks each of these:

- **One file per dashboard, in its set's folder:** `<set>/<name>.json`, as
  Grafana's *Export > Export as JSON* writes it, with *Export for sharing
  externally* off: that option replaces the datasources with inputs Git Sync
  does not fill in.
- **A fixed `uid`,** unique in the repository, 40 characters at most. It is in
  every link to the dashboard and in every customer's copy, so it never
  changes once merged.
- **No `id`.** Each Grafana numbers its own dashboards.
- **Only the datasources every customer has,** by uid: `gaas-mimir`
  (Prometheus: metrics, the uptime probes and the span metrics from traces),
  `gaas-loki` (logs) and `gaas-tempo` (traces), or a dashboard variable such
  as `${datasource}`.
- **It works for every customer.** One `main` serves them all: a panel that
  needs telemetry not every customer sends yet waits until they do.

## Changing a dashboard

1. Edit it in a Grafana that has the three datasources, then export it over the
   file, or edit the JSON.
2. Run the checks (below).
3. Open a pull request to `main`. CI runs the same checks, and a reviewer
   looks at the dashboard itself, not only the JSON.

## Checks

```sh
python3 scripts/check_test.py                 # the check's own tests
python3 scripts/check.py --base origin/main   # the rules, and no uid changed

# Grafana imports each one: the version customers run, with admin:admin.
docker run -d --name dashboards-check -p 127.0.0.1:3000:3000 grafana/grafana:13.2.1
python3 scripts/check.py --grafana http://127.0.0.1:3000
docker rm -f dashboards-check
```

[CI](.github/workflows/check.yml) runs all three on every pull request and on
`main`.
