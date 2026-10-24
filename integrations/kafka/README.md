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
lag and members. Each cluster is its own `instance`, named after the broker
address Alloy connects to, and carries its environment's name in the
`cluster` label.

The **Kafka** dashboard shows brokers, topics and partitions, messages in
by topic and consumed by group, the lag and members of each consumer group,
and replication.

It reads no broker internals (request rates, JVM): for those, run the JMX
exporter on the brokers and use the JVM integration.

## What you need

- Kafka 2.x or later (ZooKeeper or KRaft), and
  [Grafana Alloy](https://grafana.com/docs/alloy/latest/set-up/install/) on
  a machine that can reach a broker.
- A broker's address, for `KAFKA_ADDRESS`, such as `localhost:9092`.
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
| KafkaConsumerLagHigh | A consumer group is many messages behind on a topic, for 15 minutes | `consumer_lag`, 1000 messages |

## Source and licence

The replication and consumer lag alerts are adapted from grafana/jsonnet-libs'
[kafka-observ-lib](https://github.com/grafana/jsonnet-libs/tree/master/kafka-observ-lib)
(Apache-2.0): the ones that read the kafka exporter's metrics, grouped by
environment, with thresholds you can change. The other alerts, the
dashboard and this snippet are written for Telopi in this repository.
Apache-2.0, as the repository.
