# Kubernetes

Each cluster's nodes, pods and workloads, what keeps them from running, and
the logs of every pod, from an Alloy that runs in the cluster.

## What it collects

Once a minute:

- **kube-state-metrics**: each node and its condition, each pod with its
  phase, containers waiting or restarted and why, requests and limits, and
  each Deployment, StatefulSet, DaemonSet and Job with the pods it wants and
  has.
- **cAdvisor**, from each node's kubelet: containers' CPU, CPU throttling,
  memory in use and network traffic. Only these, to keep the series few.
- **The kubelet**: how full each persistent volume is.

And as they are written:

- **Logs** of every container of every pod, with the labels `namespace`,
  `pod`, `container` and `app` (the pod's `app.kubernetes.io/name` label,
  else its `app` label, else the container's name). Loki takes `app` as the
  service's name, so the alert for a service that logs many errors covers
  each app. Find them in Grafana's Explore, under Loki, with
  `{cluster="production", namespace="shop"}`.

Every series and every log line carries the cluster's name in the `cluster`
label, which is the environment's name in Telopi. The **Kubernetes:
clusters** dashboard has one row per environment (nodes, pods, restarts, CPU
and memory requested and used) and what is wrong now; **Kubernetes:
workloads** has each workload with its pods, containers that cannot start or
ran out of memory, and CPU and memory against requests and limits.

For the nodes themselves (CPU, memory, disks), add the Machines integration
to the same Alloy, or run it on each node.

## What you need

- **kube-state-metrics** in the cluster, with the label
  `app.kubernetes.io/name=kube-state-metrics` and a port named `http`, as its
  Helm chart installs it:
  `helm install kube-state-metrics prometheus-community/kube-state-metrics -n kube-system`.
- **Alloy in the cluster**, one replica, from Grafana's Helm chart
  (`helm install alloy grafana/alloy`), with this snippet as its
  configuration (`alloy.configMap.content`). Its service account may `get`,
  `list` and `watch` nodes, endpoints, services and pods, and `get`
  `nodes/proxy`, `nodes/metrics` and `pods/log`; the chart's default role
  allows all but `nodes/proxy`, which the Connect steps add.
- **One Alloy reads every pod's logs through the API server**
  (`loki.source.kubernetes`), not from the nodes' disks, so it runs as a
  Deployment with one replica and needs no host paths. That suits small and
  medium clusters. On a large or busy one, run Alloy as a DaemonSet that
  reads `/var/log/pods` on each node instead. Alloy keeps how far it has read
  on its own disk, which the chart does not keep, so after a restart it reads
  each pod's logs again from the start of what Kubernetes keeps. Loki drops
  the lines it already has; you may see a short burst of older lines.
- **An ingest key** from the Ingest keys page of the Telopi portal. Its
  username is in the snippet; put its password in a Secret and give it to
  Alloy as the environment variable `TELOPI_PASSWORD`
  (`alloy.extraEnv` with `valueFrom.secretKeyRef`).
- The cluster's name for `ENVIRONMENT`, as you call it in Telopi.

Grafana's Kubernetes monitoring Helm chart (`k8s-monitoring`) sends the same
metrics and logs, and works too: give its destination your ingest address
and key, and its `cluster.name` the environment's name.

## Alerts

| Alert | Fires when | Threshold you can change |
| --- | --- | --- |
| PodCrashLooping | A container keeps exiting and Kubernetes waits longer before each restart, for 15 minutes | |
| ImagePullBackOff | A container cannot pull its image, for 15 minutes | |
| PodNotReady | A pod stays pending, or on a node that stopped reporting | `pod_not_ready_for`, 15 minutes |
| DeploymentReplicasMismatch | A Deployment has fewer available pods than it wants, for 15 minutes | |
| StatefulSetReplicasMismatch | A StatefulSet has fewer ready pods than it wants, for 15 minutes | |
| DaemonSetNotAvailable | A DaemonSet's pod is missing on some node, for 15 minutes | |
| ContainerOOMKilled | A container was killed for using more memory than its limit | |
| JobFailed | A Job failed | |
| NodeNotReady | A node is not ready, for 15 minutes (critical) | |
| PersistentVolumeAlmostFull | A persistent volume is nearly full, for 15 minutes | `volume_percent`, 90% |
| CPUThrottlingHigh | A container's CPU limit holds it back, for 15 minutes | `throttled_percent`, 25% |

## Source and licence

Written for Telopi in this repository: the dashboards, the alert rules and
this snippet; nothing is copied from elsewhere. The metrics are those of
[kube-state-metrics](https://github.com/kubernetes/kube-state-metrics),
the kubelet and [cAdvisor](https://github.com/google/cadvisor), all
Apache-2.0.
