# Node.js

How healthy each of your Node.js processes is: how late its event loop
runs, how much heap it uses, how much time goes to garbage collection, and
whether it is down or keeps restarting, from
[prom-client](https://github.com/siimon/prom-client)'s default metrics.

## What it collects

prom-client's `collectDefaultMetrics()` measures the process, and your app
serves the result on a `/metrics` page; Alloy scrapes it once a minute:
event loop lag (percentiles), V8 heap used and total and per space,
external memory, garbage collections and their time by kind, open handles
and requests, CPU, resident memory, open files, start time and the Node.js
version. Each process is its own `instance`, named after its address, and
carries its environment's name in the `cluster` label. Any metric of your
own that the same page serves is sent too.

The **Node.js** dashboard shows the processes up, event loop lag, restarts,
handles and requests, heap, process memory, time in GC and collections, and
CPU.

## What you need

- [prom-client](https://www.npmjs.com/package/prom-client) in your app, its
  default metrics on, and a `/metrics` page. With Express:

  ```js
  const client = require('prom-client');
  client.collectDefaultMetrics();

  app.get('/metrics', async (req, res) => {
    res.set('Content-Type', client.register.contentType);
    res.end(await client.register.metrics());
  });
  ```

  Serve it where only Alloy can read it, on a port of its own if your app
  is public.
- Its address, for `NODEJS_ADDRESS`, such as `localhost:3000`. If the page
  is not at `/metrics`, change `metrics_path` in the snippet. For more
  processes, add each address to `targets`.
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
| NodejsDown | Alloy cannot scrape a process: it is down, serves no `/metrics`, or cannot be reached | `down_for`, 2 minutes |
| NodejsEventLoopLagHigh | A process's event loop runs late (99th percentile), for 10 minutes | `event_loop_lag_seconds`, 0.5 seconds |
| NodejsRestarting | A process started again more than a few times in 15 minutes | `restarts`, 2 |

## Source and licence

`NodejsDown` is adapted from grafana/jsonnet-libs'
[nodejs-mixin](https://github.com/grafana/jsonnet-libs/tree/master/nodejs-mixin)
(Apache-2.0), on Alloy's `up` instead of `absent()`, so a customer who sends
no Node.js metrics is never alerted. The other alerts, the dashboard and
this snippet are written for Telopi in this repository. Apache-2.0, as the
repository.
