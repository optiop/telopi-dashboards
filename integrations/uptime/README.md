# Uptime

Whether your websites answer, and how fast, checked by Telopi every minute
from its own cluster in Nuremberg, Germany.

## What it collects

One HTTPS request per site every minute, through a blackbox exporter that
Telopi runs: whether it succeeded, how long it took, the HTTP status, and
when the site's certificate expires. Each site is labelled with the name you
gave it (`company`) and its address (`instance`).

The **Uptime** dashboard shows which sites are up, their availability and
their response time. Each name also gets a monthly status report page.

## What you need

Nothing to install. Add your sites on the **Uptime** page of the Telopi
portal (owners and admins, up to ten), with a name and an `https` address.
The first check runs within a few minutes.

## Alerts

| Alert | Fires when | Threshold you can change |
| --- | --- | --- |
| SiteDown | Every check of a site fails, for a while (critical) | `down_for`, 3 minutes |
| CertificateExpiresSoon | A site's certificate expires within some days, for an hour | `certificate_days`, 14 days |

## Source and licence

Written for Telopi in this repository: the dashboard and the alert rules;
nothing is copied from elsewhere. The checks are the
[blackbox exporter's](https://github.com/prometheus/blackbox_exporter)
(Apache-2.0).
