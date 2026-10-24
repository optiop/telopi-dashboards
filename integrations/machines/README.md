# Machines

How busy each of your Linux machines is, and whether it is running out of
disk, memory or CPU, from Alloy running on the machine.

## What it collects

Alloy's unix exporter (`prometheus.exporter.unix`), which collects what the
Prometheus node exporter does, once a minute: CPU time by mode, load, memory,
each disk's space and I/O, each network interface's traffic and errors, and
the machine's name and kernel (`node_uname_info`). Each machine is its own
`instance`, named after its host name, and carries its environment's name in
the `cluster` label.

The **Machines** dashboard shows one row per machine and graphs over time.

## What you need

- Linux, with [Grafana Alloy](https://grafana.com/docs/alloy/latest/set-up/install/)
  installed on each machine. Alloy runs as a service and needs no open port.
- An ingest key from the Ingest keys page of the Telopi portal. Its username
  is in the snippet; set its password in the environment variable
  `TELOPI_PASSWORD` of the Alloy service (for systemd, in
  `/etc/default/alloy`).
- The environment's name, for `ENVIRONMENT`, so the dashboard and the alerts
  can tell your environments apart.

Add the snippet to Alloy's configuration (`/etc/alloy/config.alloy`) and
restart Alloy. The machine shows on the dashboard within two minutes.

A machine that already runs the Prometheus node exporter can be scraped
instead: replace `prometheus.exporter.unix` with a `prometheus.scrape` of its
address, port 9100.

## Alerts

| Alert | Fires when | Threshold you can change |
| --- | --- | --- |
| MachineSilent | A machine that sent in the last hour has sent nothing for a while: it, or its Alloy, is down or cannot reach Telopi | `silent_for`, 5 minutes |
| DiskAlmostFull | One of a machine's own disks is nearly full, for 15 minutes | `disk_percent`, 90% |
| MemoryAlmostFull | A machine's memory is nearly all in use, for 15 minutes | `memory_percent`, 90% |
| CPUBusy | A machine's CPUs are busy on average for 15 minutes | `cpu_percent`, 90% |

## Source and licence

Written for Telopi in this repository: the dashboard, the alert rules and
this snippet; nothing is copied from elsewhere. The metrics are the
[node exporter's](https://github.com/prometheus/node_exporter) (Apache-2.0),
as Alloy's unix exporter collects them.
