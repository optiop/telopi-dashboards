# Website

What your visitors' browsers report about your website: how fast pages
load, Core Web Vitals, JavaScript errors and where visitors come from.

## What it collects

The Grafana Faro Web SDK, in a short snippet on your pages, sends from each
visitor's browser: page loads and navigation, Core Web Vitals (Largest
Contentful Paint, Interaction to Next Paint, Cumulative Layout Shift),
JavaScript errors, sessions, and the site a visitor came
from (its host name only). It arrives as logs, with `source="faro"`.

The **Website** dashboard shows page loads, sessions, errors, the web vitals
and where visitors come from.

## What you need

Nothing to install or run. On the **Website** page of the Telopi portal, an
owner or admin of your organization adds each site that will send: the
address your visitors open, such as `https://www.example.com` (browsers may
send only from those). The snippet then appears on the same page: paste it
before `</head>` on every page of those sites, and the **Website** dashboard
fills as visitors come. There is no password: a web page cannot keep one, so
your sites' addresses and rate limits bound what reaches your stack.

Search and AI crawlers do not run a page's JavaScript, so they are not
counted; ad blockers can stop some visitors' browsers from sending.

## Alerts

| Alert | Fires when | Threshold you can change |
| --- | --- | --- |
| JavaScriptErrors | Your visitors hit many JavaScript errors in 5 minutes | `js_errors`, 20 |
| SlowLargestContentfulPaint | Pages take long to show their main content (75th percentile over an hour), for 15 minutes | `lcp_ms`, 4000 ms |
| SlowInteraction | Pages respond slowly to clicks and keys (75th percentile over an hour), for 15 minutes | `inp_ms`, 500 ms |
| LayoutShift | Pages move under the visitor (75th percentile over an hour), for 15 minutes | `cls`, 0.25 |

A web vital needs 20 measurements in the hour, so one slow visit is no alert.

## Source and licence

Written for Telopi in this repository: the dashboard and the alert rules;
nothing is copied from elsewhere. The browser SDK is
[Grafana Faro Web SDK](https://github.com/grafana/faro-web-sdk) (Apache-2.0).
