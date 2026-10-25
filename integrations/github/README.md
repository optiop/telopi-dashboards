# GitHub

Each deploy on GitHub, as an event beside your metrics, logs and traces, so
you can see what changed when something did.

## What it collects

GitHub sends Telopi a webhook for each deployment status, workflow run and
release. Telopi keeps the facts of the deploy and writes them as one log line
into your own Loki: the service (the repository's short name), the
environment, the status (`success`, `failure` or `in_progress`), the version
or tag, the commit, its title, who started it, the link to it on GitHub, the
repository and the time.

It never keeps your code, diffs or lists of changed files: the webhook's
other fields are dropped when it arrives.

Each event is a line with the labels
`{service_name="telopi-deploys", provider="github", environment="...", service="..."}`,
so you can query it in Explore.

## What you need

1. In the Telopi portal, on **Integrations**, open **GitHub** and add a deploy
   source. You get a payload URL and a secret, shown once.
   Set the environment on the deploy source in the portal to the environment
   this deploys to, so its deploys show on that environment's dashboards.
2. On GitHub, in the repository's (or the organization's, for all of its
   repositories) **Settings > Webhooks > Add webhook**:
   - **Payload URL**: the URL from the portal.
   - **Content type**: `application/json`.
   - **Secret**: the secret from the portal. Telopi refuses a delivery whose
     signature does not match it.
   - **Which events**: *Let me select individual events*, then
     **Deployment statuses**, **Workflow runs** and **Releases**, and nothing
     else.
3. Save. GitHub sends a ping, and the webhook's **Recent Deliveries** shows
   whether Telopi took it. The tile says *Receiving data* after your next
   deploy, workflow run or release.

## Source and licence

Written for Telopi in this repository; nothing is copied from elsewhere.
GitHub's webhook payloads are described in
[GitHub's documentation](https://docs.github.com/en/webhooks/webhook-events-and-payloads).
