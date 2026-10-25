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
| [`kubernetes/`](kubernetes) | Kubernetes: clusters (one row per environment: nodes, pods, restarts, CPU and memory requested and used; problems now, namespaces, nodes, volumes) and Kubernetes: workloads (each Deployment, StatefulSet and DaemonSet with the pods it wants and has, containers that cannot start or ran out of memory, CPU and memory against requests and limits, jobs) | always: every customer's Grafana has it, and it fills once a cluster sends kube-state-metrics (and, for usage, cAdvisor's and the kubelet's metrics), as Grafana's Kubernetes monitoring chart and Alloy send them |
| [`postgresql/`](postgresql) | PostgreSQL: servers up, connections against `max_connections`, transactions, rows, cache hit ratio, deadlocks, locks, the longest transaction and each database's size | always, and it fills once Alloy's postgres exporter sends (the PostgreSQL integration) |
| [`redis/`](redis) | Redis: instances up, clients, memory against `maxmemory`, commands per second, hit ratio, the busiest and slowest commands, evictions and keys | always, and it fills once Alloy's redis exporter sends (the Redis integration) |
| [`nginx/`](nginx) | Nginx: servers up, requests per second and per connection, connections by state, dropped connections | always, and it fills once the NGINX Prometheus exporter sends (the Nginx integration) |
| [`mysql/`](mysql) | MySQL: servers up, connections, queries per second, the busiest statements, slow queries, the InnoDB buffer pool, rows and traffic | always, and it fills once Alloy's mysql exporter sends (the MySQL integration) |
| [`kafka/`](kafka) | Kafka: brokers, topics and partitions, messages in by topic and consumed by group, consumer group lag and members, replication | always, and it fills once Alloy's kafka exporter sends (the Kafka integration) |
| [`rabbitmq/`](rabbitmq) | RabbitMQ: nodes up, messages per second and in queues, unroutable and dead-lettered messages, connections, alarms, memory, disk and file descriptors | always, and it fills once RabbitMQ's Prometheus plugin sends (the RabbitMQ integration) |
| [`jvm/`](jvm) | JVM: processes up, heap against its maximum, memory pools, time in GC and collections, threads and CPU | always, and it fills once a Java process sends the Prometheus JMX exporter's metrics (the JVM integration) |
| [`nodejs/`](nodejs) | Node.js: processes up, event loop lag, restarts, handles and requests, heap, process memory, time in GC and collections, CPU | always, and it fills once a Node.js process sends prom-client's default metrics (the Node.js integration) |

An **environment** is a Kubernetes cluster, or any machines, that send to the
customer's one Grafana under one name: the `cluster` label Alloy sets, which is
the name the customer gives it in the Telopi portal. A dashboard whose data has
it starts with an *Environment* variable over it, All by default; a series
without the label still shows under All.

**Deploys** show on Kubernetes, Machines and each integration's dashboard as
an annotation, on by default: each deploy event Telopi writes into the
customer's Loki from a deploy source (the GitHub, GitLab and Argo CD
integrations), `{service_name="telopi-deploys"}`, with its service and status
as the title and the deploy's title as the text. It follows the Environment
variable through the event's `environment` label: the environment set on the
deploy source in the portal, the same name as the `cluster` label. Under one
environment it shows that environment's deploys; under All, every deploy.

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
| [`deploys/`](alerts/deploys/loki.yaml) | A deploy that failed, from any deploy source (GitHub, GitLab, Argo CD) |
| [`machines/`](alerts/machines/mimir.yaml) | A machine that stopped sending; its disk, memory or CPU nearly used up |
| [`kubernetes/`](alerts/kubernetes/mimir.yaml) | A pod crash-looping, unable to pull its image or not starting; a Deployment, StatefulSet or DaemonSet short of pods; a container killed for memory; a failed job; a node not ready; a volume nearly full; a container held back by its CPU limit |
| [`postgresql/`](alerts/postgresql/mimir.yaml) | A server down; its connections nearly used up; deadlocks; a replica falling behind |
| [`redis/`](alerts/redis/mimir.yaml) | An instance down; its memory nearly full; connections refused; a replica that lost its primary |
| [`nginx/`](alerts/nginx/mimir.yaml) | A server down; dropping connections |
| [`mysql/`](alerts/mysql/mimir.yaml) | A server down; its connections nearly used up; a replica stopped or falling behind |
| [`kafka/`](alerts/kafka/mimir.yaml) | A cluster that stopped sending; a broker that left; under-replicated partitions; a consumer group far behind |
| [`rabbitmq/`](alerts/rabbitmq/mimir.yaml) | A node down; publishers blocked by a memory or disk alarm; memory or file descriptors nearly used up |
| [`jvm/`](alerts/jvm/mimir.yaml) | A process down; its heap nearly full; much time in GC; deadlocked threads |
| [`nodejs/`](alerts/nodejs/mimir.yaml) | A process down; its event loop running late; restarting again and again |

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

## Integrations

[`integrations/`](integrations) is the catalog the Telopi portal's
**Integrations** page shows (Telopi's ADR-0058): one tile per technology a
customer can send, with how to send it, its dashboards and its alerts. The
platform reads it from `main` as it reads the alert sets, every few minutes,
so a tile ships with its merge, without a platform release. Not connected
yet: the platform reads it, and takes its list of alert sets from it, from
its next release; until then the alert sets are listed in the platform too.

An integration is a folder `integrations/<id>/`, listed in
[`integrations/index.yaml`](integrations/index.yaml), with three files:

| File | What it is |
| --- | --- |
| `integration.yaml` | The manifest: the tile, its check, its sets and its settings (below) |
| `alloy.alloy` | The Alloy snippet the customer adds, with placeholders the portal fills or names |
| `README.md` | Its docs, which the portal shows on the tile's Install tab |

Its dashboards are a set folder at the root (`<set>/*.json`) and its alerts a
set in `alerts/<set>/`, exactly as every set above: an integration names
them, it does not hold them.

### The manifest

```yaml
id: redis                   # the folder's name: lower-case letters, digits and _
name: Redis                 # what the tile says, at most 40 characters
category: database          # database, queue, web_server, runtime, infrastructure, website or deploys
description: Memory, clients, commands and keys of each Redis.   # one line, at most 160 characters
signals: [metrics]          # some of metrics, logs, traces
check:                      # does the tenant receive it? Data in the last hour means yes
  datasource: mimir         # mimir (PromQL) or loki (LogQL)
  query: group(max_over_time(redis_up[1h]))
install: alloy              # alloy: alloy.alloy is the snippet; telopi: Telopi does it, the README says how
dashboards:                 # optional: every dashboard of its set's folder, by uid, with its title
  - uid: telopi-redis
    title: Redis
alerts: alerts/redis/mimir.yaml   # optional: its alert set's file
settings:                   # optional: the snippet's own ${NAME} placeholders, which the customer fills
  - name: REDIS_ADDRESS
    description: Where Redis listens, host and port.
    example: localhost:6379
env:                        # optional: secrets the snippet reads with sys.env("NAME"), besides TELOPI_PASSWORD
  - name: REDIS_PASSWORD
    description: The password of a Redis user that may run INFO.
```

- **The check** runs as an instant query against the customer's own Mimir or
  Loki, with its own login, and the tile says *Receiving data* when it returns
  anything. It looks over the last hour (`[1h]`), so a tile does not flicker
  between scrapes: `group(max_over_time(<a metric every target has>[1h]))` for
  metrics, `sum(count_over_time({<its streams>}[1h]))` for logs. A deploy
  source's (category `deploys`) may look over the last week (`[7d]`) instead:
  deploys are rare, and an hour would drop its tile back to *Not set up*.
- **A tile's state** is *Not set up*, *Receiving data* (the check returns
  data) or *Alerts on* (that, and the customer has its alert set on).
- **A set with no tile** (the `traces`, `logs` and `deploys` alert sets, which
  apply to whatever a customer sends) is an integration too, so the platform finds it:
  `id`, `name`, `hidden: true` and `alerts`, nothing else, and no snippet.

### The snippet

`alloy.alloy` is a whole piece of Alloy configuration a customer adds beside
their own (Alloy reads every `.alloy` file of a directory as one), sending
straight to their Telopi stack:

- **`${INGEST_URL}` and `${USERNAME}`** are filled by the portal with the
  stack's ingest address and the username of the ingest key the customer
  picks. Every snippet uses both.
- **The password is never a placeholder:** the snippet reads it with
  `sys.env("TELOPI_PASSWORD")`, and the customer sets that variable on the
  machine. Any other secret (a database password, a DSN with one) is read the
  same way and declared under `env`.
- **`${NAME}`** of the manifest's `settings` is a value the customer fills: an
  address, a port, an environment's name. Upper-case, inside a string, never a
  secret. Its `example` is what the check validates the snippet with.
- **Every component is labelled `<id>` or `<id>_<something>`**
  (`prometheus.remote_write "redis"`, `prometheus.scrape "redis_exporter"`),
  so any number of snippets share one Alloy without a clash. Each sends with
  a writer of its own (`prometheus.remote_write`, `loki.write`), to
  `${INGEST_URL}/mimir/api/v1/push` for metrics and
  `${INGEST_URL}/loki/loki/api/v1/push` for logs, and sets the `cluster`
  external label to the environment's name where its dashboards group by it.
- Scrape every minute (`scrape_interval = "60s"`): the dashboards' rates
  assume it.

### The README

The portal shows it on the tile's Install tab, so it is written for the
customer. It has these headings, which the check looks for:

- `## What it collects`: the metrics or logs, and what the dashboards show.
- `## What you need`: what the customer sets up on their side (an exporter,
  a read-only database user, a status page) and where the snippet goes.
- `## Alerts` (where it has an alert set): each alert, when it fires and the
  threshold the customer can change.
- `## Source and licence`: where the dashboards and alerts come from and
  their licence. Content forked from a mixin keeps its licence (Apache-2.0
  ones, from `grafana/jsonnet-libs` or the exporter's own) and names it here;
  nothing comes from a Grafana Cloud stack or from content whose licence
  forbids a hosted service.

Tiles show names, never logos.

### Adding an integration

1. Add its dashboards as a set folder and its alerts as `alerts/<set>/`, by
   the rules above, if it has them.
2. Add `integrations/<id>/` with the three files, and `<id>` to
   `integrations/index.yaml`.
3. Send it yourself: run the snippet against a stack, see the check's query
   return data and the dashboards fill.
4. Run the checks (below) and open a pull request. A tile without a working
   check, dashboards and alerts does not ship (ADR-0058).

[`scripts/check_integrations.py`](scripts/check_integrations.py) checks each
manifest field above, that the index lists each folder once, that the sets it
names exist and its dashboards are their whole folder, the README's headings,
the snippet's placeholders, environment variables and labels, and, given
`--alloy`, that `alloy fmt` parses the snippet and `alloy validate` takes it
with each placeholder at its example.

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

# The integrations, and Alloy takes each snippet.
python3 scripts/check_integrations_test.py    # the integration check's own tests (needs PyYAML)
python3 scripts/check_integrations.py \
  --alloy "docker run --rm -v {dir}:/snippets grafana/alloy:v1.20.0"
```

[CI](.github/workflows/check.yml) runs all of them on every pull request and on
`main`.

## Licence

[Apache-2.0](LICENSE), the licence of the mixins much of it is forked from.
Content forked from elsewhere keeps its own licence and says so: an
integration's README names its source and licence under *Source and licence*.
