# GitLab

Each deploy on GitLab, as an event beside your metrics, logs and traces, so
you can see what changed when something did.

## What it collects

GitLab sends Telopi a webhook for each deployment and pipeline event. Telopi
keeps the facts of the deploy and writes them as one log line into your own
Loki: the service (the project's short name), the environment, the status
(`success`, `failure` or `in_progress`), the version or ref, the commit, its
title, who started it, the link to it on GitLab, the project and the time.

It never keeps your code, diffs or lists of changed files: the webhook's
other fields are dropped when it arrives.

Each event is a line with the labels
`{service_name="telopi-deploys", provider="gitlab", environment="...", service="..."}`,
so you can query it in Explore.

## What you need

1. In the Telopi portal, on **Integrations**, open **GitLab** and add a deploy
   source. You get a URL and a secret token, shown once.
   Set the environment on the deploy source in the portal to the environment
   this deploys to, so its deploys show on that environment's dashboards.
2. On GitLab, in the project's (or the group's, for all of its projects;
   group webhooks need GitLab Premium) **Settings > Webhooks > Add new
   webhook**:
   - **URL**: the URL from the portal.
   - **Secret token**: the token from the portal. Telopi refuses a request
     that does not carry it.
   - **Trigger**: **Deployment events** and **Pipeline events**, and nothing
     else.
   - **SSL verification**: on.
3. Save, then **Test > Pipeline events** to send one. The tile says
   *Receiving data* once Telopi has written one.

## Source and licence

Written for Telopi in this repository; nothing is copied from elsewhere.
GitLab's webhook payloads are described in
[GitLab's documentation](https://docs.gitlab.com/user/project/integrations/webhook_events/).
