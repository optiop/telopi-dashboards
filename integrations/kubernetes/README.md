# Kubernetes

Each cluster's nodes, pods and workloads, and what keeps them from running,
from an Alloy that runs in the cluster.

**To install it, go to Connect > Kubernetes in the Telopi portal.** It walks
you through each step with your ingest key and environment filled in, and
shows when the data arrives. The snippet on this page is for a cluster that
already runs Alloy.

## What it collects

Once a minute:

- **kube-state-metrics**: each node and its condition, each pod with its
  phase, containers waiting or restarted and why, requests and limits, and
  each Deployment, StatefulSet, DaemonSet and Job with the pods it wants and
  has.
- **cAdvisor**, from each node's kubelet: containers' CPU, CPU throttling,
  memory in use and network traffic. Only these, to keep the series few.
- **The kubelet**: how full each persistent volume is.

Every series carries the cluster's name in the `cluster` label, which is the
environment's name in Telopi. The **Kubernetes: clusters** dashboard has one
row per environment (nodes, pods, restarts, CPU and memory requested and
used) and what is wrong now; **Kubernetes: workloads** has each workload with
its pods, containers that cannot start or ran out of memory, and CPU and
memory against requests and limits.

For the nodes themselves (CPU, memory, disks), add the Machines integration
to the same Alloy, or run it on each node.

## What you need

Connect > Kubernetes sets up all of this, in the namespace `telopi`, from a
machine with `kubectl` and Helm pointed at the cluster:

1. **The Helm charts** of kube-state-metrics (`prometheus-community`) and
   Alloy (`grafana`).
2. **kube-state-metrics** in the namespace `telopi`:
   `helm upgrade --install kube-state-metrics prometheus-community/kube-state-metrics --namespace telopi`.
   The snippet finds it by the label
   `app.kubernetes.io/name=kube-state-metrics` and its port named `http`, as
   the chart sets them, in any namespace.
3. **Your ingest key's password in a Secret**, `telopi-alloy`, as
   `TELOPI_PASSWORD`. The step asks for the password, so it is in no command
   and not in your shell's history. The key's username is in the snippet.
4. **Alloy's configuration in a ConfigMap**, `telopi-alloy`, under the key
   `config.alloy`: the snippet, with the cluster's name as `ENVIRONMENT`, as
   you call it in Telopi.
5. **Alloy**, one replica (`controller.type=deployment`,
   `controller.replicas=1`), from Grafana's chart, reading that ConfigMap
   (`alloy.configMap.create=false`, `alloy.configMap.name=telopi-alloy`,
   `alloy.configMap.key=config.alloy`) and that Secret
   (`alloy.envFrom[0].secretRef.name=telopi-alloy`). Its service account may
   `get`, `list` and `watch` nodes, endpoints, services and pods, which the
   chart's role allows, and `get` `nodes/proxy`, which the chart does not: a
   ClusterRole `telopi-alloy-kubelet` bound to `telopi:alloy` adds it.

Connect's last step, See it arrive, shows Arriving for metrics within two
minutes, and the Kubernetes dashboards fill.

**If Alloy already runs in your cluster**, add the snippet above to its
configuration instead, with `TELOPI_PASSWORD` in its environment and
kube-state-metrics installed as in step 2. Its service account needs the same
permissions, `nodes/proxy` included.

Grafana's Kubernetes monitoring Helm chart (`k8s-monitoring`) sends the same
metrics, and works too: give its destination your ingest address and key,
and its `cluster.name` the environment's name.

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
