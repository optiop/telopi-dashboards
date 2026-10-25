# Argo CD

Each Argo CD sync, and each application that turns degraded, as an event
beside your metrics, logs and traces, so you can see what changed when
something did.

## What it collects

Argo CD's notifications post to Telopi when an application's sync succeeds
or fails and when its health turns degraded. Telopi keeps the facts of the
deploy and writes them as one log line into your own Loki: the service (the
application's name), the environment (its destination), the status
(`success`, `failure` or `degraded`), the revision, the link to it in your
Argo CD, the repository and the time.

It never keeps your manifests, diffs or lists of changed resources: Argo CD
sends only the fields below.

Each event is a line with the labels
`{service_name="telopi-deploys", provider="argocd", environment="...", service="..."}`,
so you can query it in Explore.

## What you need

Argo CD 2.3 or later, whose notifications controller is part of it.

1. In the Telopi portal, on **Integrations**, open **Argo CD** and add a
   deploy source. You get a URL and a secret, shown once.
2. Put the secret into `argocd-notifications-secret`, in Argo CD's namespace,
   under the key `telopi-token`:

   ```sh
   kubectl -n argocd patch secret argocd-notifications-secret --type merge \
     -p '{"stringData":{"telopi-token":"<the secret from the portal>"}}'
   ```

3. Add the webhook, its template and its triggers to `argocd-notifications-cm`
   (merge these keys into yours; put the URL from the portal in `url`):

   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: argocd-notifications-cm
     namespace: argocd
   data:
     service.webhook.telopi: |
       url: <the URL from the portal>
       headers:
         - name: Content-Type
           value: application/json
         - name: Authorization
           value: Bearer $telopi-token
     template.telopi: |
       webhook:
         telopi:
           method: POST
           body: |
             {
               "app": "{{.app.metadata.name}}",
               "project": "{{.app.spec.project}}",
               "namespace": "{{.app.spec.destination.namespace}}",
               "cluster": "{{or .app.spec.destination.name .app.spec.destination.server}}",
               "revision": "{{with .app.status.sync.revision}}{{.}}{{end}}",
               "repo": "{{with .app.spec.source}}{{.repoURL}}{{end}}",
               "phase": "{{with .app.status.operationState}}{{.phase}}{{end}}",
               "sync": "{{.app.status.sync.status}}",
               "health": "{{.app.status.health.status}}",
               "url": "{{.context.argocdUrl}}/applications/{{.app.metadata.name}}"
             }
     trigger.on-sync-succeeded: |
       - when: app.status.operationState != nil and app.status.operationState.phase in ['Succeeded']
         send: [telopi]
     trigger.on-sync-failed: |
       - when: app.status.operationState != nil and app.status.operationState.phase in ['Error', 'Failed']
         send: [telopi]
     trigger.on-health-degraded: |
       - when: app.status.health.status == 'Degraded'
         send: [telopi]
   ```

   If you already have these triggers (from Argo CD's catalog, for Slack or
   email), keep yours and add `telopi` to each one's `send` list instead.

4. Subscribe each application whose deploys you want, with these annotations
   on the `Application`:

   ```yaml
   metadata:
     annotations:
       notifications.argoproj.io/subscribe.on-sync-succeeded.telopi: ""
       notifications.argoproj.io/subscribe.on-sync-failed.telopi: ""
       notifications.argoproj.io/subscribe.on-health-degraded.telopi: ""
   ```

   The tile says *Receiving data* after the next sync of one of them.

## Source and licence

Written for Telopi in this repository; nothing is copied from elsewhere.
The triggers' conditions are those of
[Argo CD's notifications catalog](https://argo-cd.readthedocs.io/en/stable/operator-manual/notifications/catalog/)
(Apache-2.0).
