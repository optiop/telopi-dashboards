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
classes, CPU and open files. Alloy sends only the metrics the dashboard,
the alerts and the tile's check read, and drops the rest. Each process is
its own `instance`: an agent on the same machine as Alloy (`localhost`) is
named after the machine and its port, any other after its address. Each
carries its environment's name in the `cluster` label.

The agent can also turn the process's own MBeans into metrics (Kafka's,
Tomcat's, your own). The configuration below turns that off, and the
snippet drops any that come anyway: an MBean can become thousands of
series.

The **JVM** dashboard shows the processes up, heap against its maximum,
memory pools, time in GC and collections, threads and CPU.

## What you need

- The agent's jar, version 1.0 or later (the metric names the dashboard
  reads are 1.x's), from the
  [JMX exporter's releases](https://github.com/prometheus/jmx_exporter/releases),
  for example `jmx_prometheus_javaagent-1.7.0.jar`, and next to it a
  configuration file that turns no MBean into a metric, so only the JVM's
  own metrics are served:

  ```yaml
  # config.yaml: the JVM's own metrics (jvm_*, process_*) and none of its MBeans.
  excludeObjectNames: ["*:*"]
  ```

- The process started with the agent listening on 127.0.0.1 only, so
  nothing outside the machine reads it, for example:

  ```sh
  java -javaagent:/opt/jmx/jmx_prometheus_javaagent-1.7.0.jar=127.0.0.1:9404:/opt/jmx/config.yaml -jar app.jar
  ```

  For a program you do not start yourself, put the same `-javaagent:...`
  in its `JAVA_OPTS` (or, for Kafka, `KAFKA_OPTS`).
- The agent's address, for `JVM_ADDRESS`: `localhost:9404`, with Alloy on
  the same machine. For more processes, add each address to `targets`.
- [Grafana Alloy](https://grafana.com/docs/alloy/latest/set-up/install/) on
  that machine.
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
| JvmHeapNearlyFull | A process's heap stays nearly full for 20 minutes, collections included (a heap that fills and empties again, as with `-Xms` equal to `-Xmx`, does not alert) | `heap_percent`, 95% |
| JvmGcTimeHigh | A process spends much of its time in garbage collection pauses, for 10 minutes (concurrent collectors, which do not stop it, are left out) | `gc_percent`, 10% |
| JvmThreadsDeadlocked | A process has deadlocked threads, for 2 minutes | |

## Source and licence

The heap and deadlock alerts are adapted from grafana/jsonnet-libs'
[jvm-observ-lib](https://github.com/grafana/jsonnet-libs/tree/master/jvm-observ-lib)
(Apache-2.0): for the JMX exporter's metric names only, grouped by
environment, with a threshold you can change. The other alerts, the
dashboard and this snippet are written for Telopi in this repository.
Apache-2.0, as the repository.
