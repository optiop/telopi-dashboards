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
| [`nodes/`](nodes) | Machines: CPU, load, memory, disks and network of each machine, one row per machine and graphs over time | always: every customer's Grafana has it, and it fills once their machines send the Prometheus node exporter's metrics or Alloy's unix exporter's (Alloy's Kubernetes monitoring includes it) |

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
- **Rates read at least four scrapes.** Alloy scrapes every minute, so every
  query with `$__rate_interval` sets its *Min step* to `1m` (`"interval": "1m"`
  on the target): Grafana then takes a minute as the scrape interval, and a
  rate's window holds enough points. Without it Grafana assumes 15 seconds
  and the graph is empty.
- **It works for every customer.** One `main` serves them all: a panel that
  needs telemetry not every customer sends yet waits until they do.

## Changing a dashboard

1. Edit it in a Grafana that has the three datasources, then export it over the
   file, or edit the JSON.
2. Run the checks (below).
3. Open a pull request to `main`. CI runs the same checks, and a reviewer
   looks at the dashboard itself, not only the JSON.

## Alert rules

[`alerts/`](alerts) holds the alert rules every customer gets beside their
dashboards (Telopi's ADR-0045): one folder per set, one rule group per set.
The file's name says which ruler evaluates it, per customer, over that
customer's data only: `mimir.yaml` (PromQL, over metrics, the uptime probes
and the span metrics from traces) or `loki.yaml` (LogQL, over logs and the
browser telemetry).

| Set | Alerts |
| --- | --- |
| [`uptime/`](alerts/uptime/mimir.yaml) | A checked site down; its certificate expiring |
| [`website/`](alerts/website/loki.yaml) | JavaScript errors; Largest Contentful Paint, Interaction to Next Paint or Cumulative Layout Shift turning poor |
| [`traces/`](alerts/traces/mimir.yaml) | A service failing its requests, or slow |
| [`logs/`](alerts/logs/loki.yaml) | A service logging many errors |
| [`machines/`](alerts/machines/mimir.yaml) | A machine that stopped sending; its disk, memory or CPU nearly used up |

Not connected yet: the platform's reconciler, which writes each set into each
customer's rulers every five minutes, in a namespace of its own (`telopi`),
comes next. Then, as for the dashboards, a merge to `main` reaches every
customer, and so does a mistake.

### Thresholds

A set's `thresholds` name the values a customer may change in the Telopi
portal, each with its default and what it means; a rule says `${name}` where
the value goes. The platform puts each customer's value in, or the default.

### Rules for a rule

[`scripts/check_alerts.py`](scripts/check_alerts.py) checks each of these:

- **Every rule is an alert,** with a `severity` label, `critical` or
  `warning`, and a `summary` annotation: the portal lists it, and the mail
  and the Slack message lead with it.
- **Alert names are unique** across the sets, and each set has one group,
  named after its folder.
- **Every `${name}` is one of the set's thresholds,** and every threshold is
  used. A default is a number or a duration such as `5m`.
- **Mimir or Loki takes it,** with every threshold at its default: promtool
  parses each Mimir set, and a Loki of the platform's version, with the
  platform's ruler settings ([`scripts/loki-check.yaml`](scripts/loki-check.yaml)),
  takes each Loki set through its ruler API.

And one the check cannot: **a rule works for every customer,** firing on a
real problem and never on a customer who sends none of that telemetry (no
`absent()`). Before a new rule reaches customers it runs on Telopi's own
tenants for a week without paging anyone.

## Checks

```sh
python3 scripts/check_test.py                 # the check's own tests
python3 scripts/check.py --base origin/main   # the rules, and no uid changed
python3 scripts/check_alerts_test.py          # the alert check's own tests (needs PyYAML)
python3 scripts/check_alerts.py               # the alert rules' own rules

# Grafana imports each one: the version customers run, with admin:admin.
docker run -d --name dashboards-check -p 127.0.0.1:3000:3000 grafana/grafana:13.2.1
python3 scripts/check.py --grafana http://127.0.0.1:3000
docker rm -f dashboards-check

# promtool parses each Mimir set, and Loki's ruler takes each Loki set.
docker run -d --name loki-check -p 127.0.0.1:3100:3100 \
  -v "$PWD/scripts/loki-check.yaml:/etc/loki/check.yaml:ro" \
  grafana/loki:3.7.7 -config.file=/etc/loki/check.yaml
python3 scripts/check_alerts.py --loki http://127.0.0.1:3100 \
  --promtool "docker run --rm -v {dir}:/rules --entrypoint promtool prom/prometheus:v3.5.0"
docker rm -f loki-check
```

[CI](.github/workflows/check.yml) runs all of them on every pull request and on
`main`.
