# Redis

How busy each of your Redis instances is, how full its memory is, and
whether it is down or refusing clients, from Alloy asking Redis for its
`INFO`.

## What it collects

Alloy's built-in redis exporter (`prometheus.exporter.redis`) runs `INFO`
and a few other read-only commands once a minute: whether Redis answers
(`redis_up`), memory used against `maxmemory`, connected and blocked
clients, rejected connections, commands per second by command and their
time, key hits and misses, evicted and expired keys, keys per database,
network traffic and replication. Each instance is its own `instance`, named
after its address, and carries its environment's name in the `cluster`
label. Valkey answers the same way.

The **Redis** dashboard shows the instances up, clients, memory, commands
per second, the hit ratio, the busiest and slowest commands, evictions and
keys.

## What you need

- Redis 5 or later (or Valkey), and [Grafana Alloy](https://grafana.com/docs/alloy/latest/set-up/install/)
  on a machine that can reach it.
- Its address, for `REDIS_ADDRESS`, such as `localhost:6379`.
- If Redis has a password, it in the environment variable `REDIS_PASSWORD`
  of the Alloy service (for systemd, in `/etc/default/alloy`). With ACLs, a
  user that may run `INFO`, `CONFIG GET`, `SLOWLOG`, `LATENCY` and `CLIENT`
  is enough; leave the variable empty when Redis has no password.
- An ingest key from the Ingest keys page of the Telopi portal. Its username
  is in the snippet; set its password in the environment variable
  `TELOPI_PASSWORD` of the Alloy service.
- The environment's name, for `ENVIRONMENT`.

Add the snippet to Alloy's configuration (`/etc/alloy/config.alloy`) and
restart Alloy. Redis shows on the dashboard within two minutes. For another
instance, copy the three blocks with a new label (`redis_cache`, say).

## Alerts

| Alert | Fires when | Threshold you can change |
| --- | --- | --- |
| RedisDown | Alloy cannot reach Redis: it is down, refuses the password, or cannot be reached | `down_for`, 2 minutes |
| RedisMemoryNearlyFull | Most of `maxmemory` is in use, for 10 minutes (only where `maxmemory` is set) | `memory_percent`, 90% |
| RedisRejectingConnections | Redis refused connections in the last 5 minutes because `maxclients` was reached | |
| RedisReplicaLinkDown | A replica has not been connected to its primary for 5 minutes | |

## Source and licence

The alert rules are adapted from the
[redis-mixin](https://github.com/grafana/jsonnet-libs/tree/master/redis-mixin)
of grafana/jsonnet-libs (Apache-2.0): its memory and replica link alerts,
read from the exporter's own metrics instead of Kubernetes', grouped by
environment, with thresholds you can change. The dashboard and this snippet
are written for Telopi in this repository. The metrics are those of the
[redis exporter](https://github.com/oliver006/redis_exporter) (MIT) that
Alloy embeds; nothing of it is copied here. Apache-2.0, as the repository.
