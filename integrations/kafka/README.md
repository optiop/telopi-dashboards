# Kafka

What is written to and read from each of your Kafka clusters, whether its
partitions are fully replicated, and how far behind each consumer group is,
from Alloy reading the cluster's metadata and offsets.

## What it collects

Alloy's built-in kafka exporter (`prometheus.exporter.kafka`, the
[kafka exporter](https://github.com/danielqsj/kafka_exporter)) connects to a
broker once a minute, as a Kafka client, and reads the cluster's metadata
and offsets: the brokers, each topic's partitions, their offsets, leaders,
replicas and in-sync replicas, and each consumer group's committed offsets,
lag and members. It reads the topics and groups that `KAFKA_TOPICS` and
`KAFKA_GROUPS` match, and never Kafka's internal topics (`__` and on). Each
cluster is its own `instance`, named after the broker address Alloy
connects to (a broker on the same machine as Alloy, `localhost`, after the
machine and its port), and carries its environment's name in the `cluster`
label.

**How many series.** Per topic of *P* partitions, 4 × *P* + 1 (offsets,
replicas, in-sync replicas and under-replication per partition, and the
partition count); per consumer group, 1, and 2 per topic it reads (offset
and lag, summed over partitions); 1 per broker, and 2 for the cluster. A cluster of 50 topics
of 12 partitions, read by 20 groups of 5 topics each, sends about 2,700.
Alloy drops the other per-partition series the exporter makes (leaders,
oldest offsets, and each group's offset and lag per partition), which
nothing here reads. To send fewer, narrow `KAFKA_TOPICS` and
`KAFKA_GROUPS`.

The **Kafka** dashboard shows brokers, topics and partitions, messages in
by topic and consumed by group, the lag and members of each consumer group,
and replication.

It reads no broker internals. For the brokers' heap, garbage collection
and threads, run the JMX exporter's agent on them and use the JVM
integration; their request rates are not covered.

## What you need

- Kafka 2.x or later (ZooKeeper or KRaft), and
  [Grafana Alloy](https://grafana.com/docs/alloy/latest/set-up/install/) on
  a machine that can reach a broker.
- A broker's address, for `KAFKA_ADDRESS`, such as `localhost:9092`.
- Which topics and consumer groups to read, as regular expressions, for
  `KAFKA_TOPICS` and `KAFKA_GROUPS`: `.*` for all, or `orders|billing.*`.
- On a cluster with ACLs, a principal that may only describe the cluster,
  its topics and its groups, which is all the exporter does:

  ```sh
  kafka-acls.sh --bootstrap-server localhost:9092 --add --allow-principal User:telopi --operation Describe --cluster
  kafka-acls.sh --bootstrap-server localhost:9092 --add --allow-principal User:telopi --operation Describe --topic '*'
  kafka-acls.sh --bootstrap-server localhost:9092 --add --allow-principal User:telopi --operation Describe --group '*'
  ```

  With SASL or TLS, add the matching arguments of
  [`prometheus.exporter.kafka`](https://grafana.com/docs/alloy/latest/reference/components/prometheus/prometheus.exporter.kafka/)
  (`use_sasl`, `sasl_username`, `use_tls` and so on), and read the password
  with `sys.env`, never written in the file.
- An ingest key from the Ingest keys page of the Telopi portal. Its username
  is in the snippet; set its password in the environment variable
  `TELOPI_PASSWORD` of the Alloy service (for systemd, in
  `/etc/default/alloy`).
- The environment's name, for `ENVIRONMENT`.

Add the snippet to Alloy's configuration (`/etc/alloy/config.alloy`) and
restart Alloy, once per Kafka cluster. The cluster shows on the dashboard
within two minutes.

## Alerts

| Alert | Fires when | Threshold you can change |
| --- | --- | --- |
| KafkaSilent | A cluster that sent in the last hour has sent nothing for a while: its brokers, or the Alloy that reads them, are down or cannot be reached | `silent_for`, 5 minutes |
| KafkaBrokerLost | The cluster has fewer brokers than at any time in the last hour, for 5 minutes | |
| KafkaUnderReplicatedPartitions | A topic has partitions with fewer in-sync replicas than replicas, for 5 minutes | |
| KafkaConsumerLagHigh | A consumer group has been many messages behind on a topic for all of the last 30 minutes, and is not catching up | `consumer_lag`, 1000 messages |

## Source and licence

The replication and consumer lag alerts are adapted from grafana/jsonnet-libs'
[kafka-observ-lib](https://github.com/grafana/jsonnet-libs/tree/master/kafka-observ-lib)
(Apache-2.0): the ones that read the kafka exporter's metrics, grouped by
environment, with thresholds you can change. The other alerts, the
dashboard and this snippet are written for Telopi in this repository.
Apache-2.0, as the repository.
