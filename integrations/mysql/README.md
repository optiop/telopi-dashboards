# MySQL

How busy each of your MySQL or MariaDB servers is, and whether it is down,
short of connections, or a replica that stopped, from Alloy reading the
server's own status.

## What it collects

Alloy's built-in mysql exporter (`prometheus.exporter.mysql`, the
Prometheus [mysqld exporter](https://github.com/prometheus/mysqld_exporter))
connects to the server once a minute and reads its global status and
variables, InnoDB's and, on a replica, the replication status: whether it
answers (`mysql_up`), connections against `max_connections`, aborted
connections, statements by type, slow queries, temporary tables on disk,
the InnoDB buffer pool and row operations, traffic, and replication lag.
Alloy sends only the metrics the dashboard, the alerts and the tile's check
read, about twenty-five, and drops the rest (the exporter reads several
hundred status variables). Each server is its own `instance`: a server on
the same machine as Alloy (`localhost`) is named after the machine and its
port, any other after its address. Each carries its environment's name in
the `cluster` label.

The **MySQL** dashboard shows the servers up, connections, queries per
second, the busiest statements, slow queries, the buffer pool hit ratio and
size, InnoDB rows and network traffic.

## What you need

- MySQL 5.7 or later, or MariaDB 10.5 or later, and
  [Grafana Alloy](https://grafana.com/docs/alloy/latest/set-up/install/) on a
  machine that can reach it.
- A monitoring user that may read the status and nothing else, and only
  from where Alloy runs (here the same machine; otherwise Alloy's address
  in place of `127.0.0.1`):

  ```sql
  CREATE USER 'telopi'@'127.0.0.1' IDENTIFIED BY 'choose-one' WITH MAX_USER_CONNECTIONS 3;
  GRANT PROCESS, REPLICATION CLIENT ON *.* TO 'telopi'@'127.0.0.1';
  GRANT SELECT ON performance_schema.* TO 'telopi'@'127.0.0.1';
  ```

  On MariaDB 10.5 or later, where `REPLICATION CLIENT` became
  `BINLOG MONITOR`, grant `REPLICA MONITOR` too, so that it may read
  `SHOW REPLICA STATUS`:

  ```sql
  GRANT REPLICA MONITOR ON *.* TO 'telopi'@'127.0.0.1';
  ```

- Its connection string in the environment variable `MYSQL_DSN` of the
  Alloy service, such as `telopi:choose-one@(127.0.0.1:3306)/`. For systemd,
  set it in `/etc/default/alloy`.
- An ingest key from the Ingest keys page of the Telopi portal. Its username
  is in the snippet; set its password in the environment variable
  `TELOPI_PASSWORD` of the Alloy service.
- The environment's name, for `ENVIRONMENT`.

Add the snippet to Alloy's configuration (`/etc/alloy/config.alloy`) and
restart Alloy. The server shows on the dashboard within two minutes. For
another server, copy the five blocks with a new label (`mysql_orders`, say)
and its own connection string.

## Alerts

| Alert | Fires when | Threshold you can change |
| --- | --- | --- |
| MySQLDown | Alloy cannot query a server: it is down, refuses the monitoring user, or cannot be reached | `down_for`, 2 minutes |
| MySQLConnectionsNearlyUsed | Most of `max_connections` is in use, for 10 minutes | `connections_percent`, 80% |
| MySQLReplicationStopped | A replica's I/O or SQL thread has been stopped for 5 minutes | |
| MySQLReplicationLagging | A replica is far behind its source, for 5 minutes | `replication_lag_seconds`, 300 |

## Source and licence

`MySQLDown` is adapted from the `mysqld-mixin` of
[prometheus/mysqld_exporter](https://github.com/prometheus/mysqld_exporter/tree/main/mysqld-mixin)
(Apache-2.0), grouped by environment with a threshold you can change. The
other alerts, the dashboard and this snippet are written for Telopi in this
repository, on the same exporter's metrics. Apache-2.0, as the repository.
