# RabbitMQ

How many messages each of your RabbitMQ nodes moves and holds, and whether
it is down, blocking publishers, or running out of memory, from RabbitMQ's
own Prometheus plugin.

## What it collects

RabbitMQ's built-in `rabbitmq_prometheus` plugin serves the node's metrics
on port 15692, and Alloy scrapes them once a minute: messages published,
delivered and acknowledged, messages ready and unacknowledged in queues,
unroutable and dead-lettered messages, connections, channels, consumers and
queues, memory against the high watermark, free disk against its limit, file
descriptors, and the memory and disk alarms. They are totals per node, not
per queue: each node counts the queues whose leader it hosts, so in a
cluster the nodes' totals add up to the cluster's, which is how the
dashboard shows them. Each node is its own `instance`: a node on the same
machine as Alloy (`localhost`) is named after the machine and its port,
any other after its address. Each carries its environment's name in the
`cluster` label.

The **RabbitMQ** dashboard shows the nodes up, messages per second and in
queues, unroutable and dead-lettered messages, connections, alarms, memory,
disk and file descriptors.

## What you need

- RabbitMQ 3.8 or later, with the Prometheus plugin on. It is on in the
  official Docker images; elsewhere:

  ```sh
  rabbitmq-plugins enable rabbitmq_prometheus
  ```

- Its address, for `RABBITMQ_ADDRESS`, such as `localhost:15692`. In a
  cluster, scrape every node: add each node's address to `targets`.
- [Grafana Alloy](https://grafana.com/docs/alloy/latest/set-up/install/) on
  a machine that can reach port 15692.
- An ingest key from the Ingest keys page of the Telopi portal. Its username
  is in the snippet; set its password in the environment variable
  `TELOPI_PASSWORD` of the Alloy service (for systemd, in
  `/etc/default/alloy`).
- The environment's name, for `ENVIRONMENT`.

Add the snippet to Alloy's configuration (`/etc/alloy/config.alloy`) and
restart Alloy. The node shows on the dashboard within two minutes.

## Alerts

| Alert | Fires when | Threshold you can change |
| --- | --- | --- |
| RabbitMQDown | Alloy cannot scrape a node: it is down, its plugin is off, or it cannot be reached | `down_for`, 2 minutes |
| RabbitMQPublishersBlocked | A memory or disk alarm is on, so the node blocks every publisher | |
| RabbitMQMemoryHigh | A node uses most of its memory high watermark, for 5 minutes | `memory_percent`, 90% |
| RabbitMQFileDescriptorsHigh | A node uses over 90% of its file descriptors, for 5 minutes | |

## Source and licence

The memory and file descriptor alerts are adapted from grafana/jsonnet-libs'
[rabbitmq-mixin](https://github.com/grafana/jsonnet-libs/tree/master/rabbitmq-mixin)
(Apache-2.0), grouped by environment, with a threshold you can change. The
other alerts, the dashboard and this snippet are written for Telopi in this
repository; nothing is taken from RabbitMQ's own dashboards, which are under
another licence. Apache-2.0, as the repository.
