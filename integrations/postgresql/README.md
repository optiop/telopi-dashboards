# PostgreSQL

How busy each of your PostgreSQL servers is, and whether it is down, short of
connections or deadlocking, from Alloy reading PostgreSQL's own statistics.

## What it collects

Alloy's built-in postgres exporter (`prometheus.exporter.postgres`, the
Prometheus [postgres exporter](https://github.com/prometheus-community/postgres_exporter))
connects to the server once a minute and reads its statistics views:
whether it answers (`pg_up`), connections by state, commits and rollbacks,
rows read and written, cache hits, deadlocks and conflicts, locks by mode,
the oldest open transaction, each database's size, replication lag, and the
server's settings. Each server is its own `instance`, named after its
connection string without the password, and carries its environment's name
in the `cluster` label.

The **PostgreSQL** dashboard shows the servers up, connections against
`max_connections`, transactions, rows, the cache hit ratio, deadlocks, locks,
the longest transaction and the size of each database.

## What you need

- PostgreSQL 10 or later, and [Grafana Alloy](https://grafana.com/docs/alloy/latest/set-up/install/)
  on a machine that can reach it.
- A monitoring user. `pg_monitor` lets it read the statistics and nothing
  else:

  ```sql
  CREATE USER telopi WITH PASSWORD 'choose-one';
  GRANT pg_monitor TO telopi;
  ```

- Its connection string in the environment variable `POSTGRES_DSN` of the
  Alloy service, such as
  `postgresql://telopi:choose-one@localhost:5432/postgres?sslmode=disable`
  (use `sslmode=require` when the server takes TLS). For systemd, set it in
  `/etc/default/alloy`.
- An ingest key from the Ingest keys page of the Telopi portal. Its username
  is in the snippet; set its password in the environment variable
  `TELOPI_PASSWORD` of the Alloy service.
- The environment's name, for `ENVIRONMENT`.

Add the snippet to Alloy's configuration (`/etc/alloy/config.alloy`) and
restart Alloy. The server shows on the dashboard within two minutes. For
more than one server, add each connection string to `data_source_names`.

## Alerts

| Alert | Fires when | Threshold you can change |
| --- | --- | --- |
| PostgreSQLDown | Alloy cannot query a server: it is down, refuses the monitoring user, or cannot be reached | `down_for`, 2 minutes |
| PostgreSQLConnectionsNearlyUsed | Most of `max_connections` (less those reserved for superusers) is in use, for 10 minutes | `connections_percent`, 80% |
| PostgreSQLDeadlocks | A database has many deadlocks a minute, for 5 minutes | `deadlocks_per_minute`, 5 |
| PostgreSQLReplicationLagging | A replica has replayed nothing newer than a while ago, for 5 minutes | `replication_lag_seconds`, 3600 |

## Source and licence

The alert rules are adapted from the `postgres_mixin` of
[prometheus-community/postgres_exporter](https://github.com/prometheus-community/postgres_exporter/tree/master/postgres_mixin)
(Apache-2.0): fewer of them, grouped by environment, with thresholds you can
change. The dashboard and this snippet are written for Telopi in this
repository, on the same exporter's metrics. Apache-2.0, as the repository.
