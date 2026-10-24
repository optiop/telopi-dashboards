# Nginx

How many requests and connections each of your Nginx servers handles, and
whether it is down or dropping connections, from Nginx's own `stub_status`
page.

## What it collects

The [NGINX Prometheus exporter](https://github.com/nginxinc/nginx-prometheus-exporter)
reads Nginx's `stub_status` page, and Alloy scrapes the exporter once a
minute: whether Nginx answers (`nginx_up`), requests, connections accepted
and handled, and open connections reading, writing and waiting. Each server
is its own `instance`: an exporter on the same machine as Alloy
(`localhost`) is named after the machine and its port, any other after its
address. Each carries its environment's name in the `cluster` label.

The **Nginx** dashboard shows the servers up, requests per second, requests
per connection, connections by state, and connections dropped.

`stub_status` has no status codes or response times. For those, send
Nginx's access log to Telopi as logs.

## What you need

- Nginx with the `stub_status` module (built into the official packages
  and images). Serve it where only the exporter can read it, for example:

  ```nginx
  server {
    listen 127.0.0.1:8080;
    location = /stub_status { stub_status; }
  }
  ```

- The NGINX Prometheus exporter next to Nginx, pointed at that page. With
  Docker:

  ```sh
  docker run -d --network host nginx/nginx-prometheus-exporter:1.5.1 \
    --web.listen-address=127.0.0.1:9113 \
    --nginx.scrape-uri=http://127.0.0.1:8080/stub_status
  ```

  It listens on 127.0.0.1, port 9113, so only this machine reads it; its
  address is `NGINX_EXPORTER_ADDRESS`, such as `localhost:9113`, with Alloy
  on the same machine.
- [Grafana Alloy](https://grafana.com/docs/alloy/latest/set-up/install/) on
  a machine that can reach the exporter.
- An ingest key from the Ingest keys page of the Telopi portal. Its username
  is in the snippet; set its password in the environment variable
  `TELOPI_PASSWORD` of the Alloy service (for systemd, in
  `/etc/default/alloy`).
- The environment's name, for `ENVIRONMENT`.

Add the snippet to Alloy's configuration (`/etc/alloy/config.alloy`) and
restart Alloy. Nginx shows on the dashboard within two minutes. For more
servers, add each exporter's address to `targets`.

## Alerts

| Alert | Fires when | Threshold you can change |
| --- | --- | --- |
| NginxDown | The exporter cannot read `stub_status`, or Alloy cannot reach the exporter | `down_for`, 2 minutes |
| NginxDroppingConnections | Nginx accepts connections it does not handle, for 5 minutes: `worker_connections` or the open files limit is reached | |

## Source and licence

The dashboard is adapted from the one in
[nginxinc/nginx-prometheus-exporter](https://github.com/nginxinc/nginx-prometheus-exporter/tree/main/grafana)
(Apache-2.0): the same panels, grouped by environment, in this repository's
style, with requests per connection and dropped connections added. The
alert rules and this snippet are written for Telopi in this repository.
Apache-2.0, as the repository.
