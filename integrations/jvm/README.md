# JVM

How much memory each of your Java processes uses, how much of its time goes
to garbage collection, and whether it is down, out of heap or deadlocked,
from the Prometheus JMX exporter running inside it. Kotlin, Scala, Clojure
and any other JVM language work the same way.

## What it collects

The [Prometheus JMX exporter](https://github.com/prometheus/jmx_exporter)
runs in the process as a Java agent and serves its metrics on a port of
your choice; Alloy scrapes them once a minute: heap and non-heap memory
used, committed and maximum, each memory pool, garbage collections and
their time per collector, threads (live, daemon, deadlocked, by state),
classes, CPU and open files. Each process is its own `instance`, named after
the agent's address, and carries its environment's name in the `cluster`
label.

The agent also turns the process's own MBeans into metrics (Kafka's,
Tomcat's, your own), as its configuration says; they are sent too, and you
can graph them in your own dashboards.

The **JVM** dashboard shows the processes up, heap against its maximum,
memory pools, time in GC and collections, threads and CPU.

## What you need

- The agent's jar, `jmx_prometheus_javaagent-<version>.jar`, from the
  [JMX exporter's releases](https://github.com/prometheus/jmx_exporter/releases),
  and a configuration file next to it. The smallest, which exports every
  MBean, is:

  ```yaml
  rules:
    - pattern: ".*"
  ```

- The process started with the agent, its port and that file, for example:

  ```sh
  java -javaagent:/opt/jmx/jmx_prometheus_javaagent.jar=9404:/opt/jmx/config.yaml -jar app.jar
  ```

  For a program you do not start yourself, put the same `-javaagent:...`
  in its `JAVA_OPTS` (or, for Kafka, `KAFKA_OPTS`).
- The agent's address, for `JVM_ADDRESS`, such as `localhost:9404`. For
  more processes, add each address to `targets`.
- [Grafana Alloy](https://grafana.com/docs/alloy/latest/set-up/install/) on
  a machine that can reach that port.
- An ingest key from the Ingest keys page of the Telopi portal. Its username
  is in the snippet; set its password in the environment variable
  `TELOPI_PASSWORD` of the Alloy service (for systemd, in
  `/etc/default/alloy`).
- The environment's name, for `ENVIRONMENT`.

Add the snippet to Alloy's configuration (`/etc/alloy/config.alloy`) and
restart Alloy. The process shows on the dashboard within two minutes.

## Alerts

| Alert | Fires when | Threshold you can change |
| --- | --- | --- |
| JvmDown | Alloy cannot scrape a process: it is down, runs without the agent, or cannot be reached | `down_for`, 2 minutes |
| JvmHeapNearlyFull | A process uses most of its maximum heap, for 10 minutes | `heap_percent`, 90% |
| JvmGcTimeHigh | A process spends much of its time collecting garbage, for 10 minutes | `gc_percent`, 10% |
| JvmThreadsDeadlocked | A process has deadlocked threads, for 2 minutes | |

## Source and licence

The heap and deadlock alerts are adapted from grafana/jsonnet-libs'
[jvm-observ-lib](https://github.com/grafana/jsonnet-libs/tree/master/jvm-observ-lib)
(Apache-2.0): for the JMX exporter's metric names only, grouped by
environment, with a threshold you can change. The other alerts, the
dashboard and this snippet are written for Telopi in this repository.
Apache-2.0, as the repository.
