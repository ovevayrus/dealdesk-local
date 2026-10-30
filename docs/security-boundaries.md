# Local demo boundaries

DealDesk Local is a single-user demonstration with synthetic data. Keep real customer documents, credentials, cost data and model weights outside this repository. The fixture accounts and role switcher do not provide production identity or authorization.

## HTTP access

The Python server rejects a non-loopback `DEALDESK_HOST`. It accepts local Host names and same-origin browser requests. Browser requests carrying another Origin or cross-origin Fetch Metadata fail before state changes. A top-level GET/HEAD document navigation with no Origin is allowed so a user can open the demo from another page; cross-origin writes and subresource requests remain refused. Local CLI/agent requests can omit Origin. These checks help contain an accidental browser request; they do not isolate the application from another process running as you. Do not expose this demo through a tunnel or reverse proxy.

HTTP bodies are limited to 16 KiB, including streamed bodies. Chat/search text is limited to 2,000 characters; tool search returns at most 20 passages with at most 10 short document-type filters. Forecast horizon is 1–24 months. Pricing validates its own monetary and policy inputs after the request-size checks. Unknown tool arguments fail rather than being retained.

The most recent 200 chat/event messages are retained for display. Older transient messages are removed when a new message is recorded. Immutable quote versions and review records are separate and are not pruned by this limit. Reset explicitly clears the synthetic demo, including those records. This is not a production financial audit store.

## Models and agent permissions

Scripted mode makes no model call. Optional Python model wording accepts configured loopback/private-network/`.local` or explicitly allowed hosts, refuses redirects and system proxies, and falls back to labeled templates. A private-network host is another machine: verify it before sending confidential material. An explicit allowed-host entry is a trust decision, not proof of locality.

At most two model HTTP requests run at once per Python process. Responses over 1 MiB fail; requests have a configured timeout of 1–60 seconds and no automatic retry. Chat asks for at most 350 output tokens. These are local work limits, not a provider spending control. The numerical engine controls decisions; checking the numbers in prose cannot validate every semantic statement a model might make.

The checked-in OpenClaw skill names four tools and treats retrieved passages as untrusted evidence. It is guidance for the external agent, not a sandbox. The prior GB10 run used unsandboxed OpenClaw. The Qwen launcher trusts acquired model code and a container image (`--trust-remote-code`, host IPC, GPU access). Inspect the real runtime permissions, image digest, model revision and mounted directories before using it. This update does not reconfigure that machine or assert a completed offline test.

## Optional Astro viewer

The viewer is a separate demonstration with fixture identities selected by an unsigned `dd_actor` cookie. Anyone who can reach it can choose a demonstration role. Its account/classification filters test projections within that assumed role; they do not authenticate a person. Keep it on loopback with synthetic data.

Normal viewer startup does not install an egress boundary. `start:offline` preloads checks for common Node network APIs in that process. It does not sandbox the operating system, native modules, subprocesses, model containers or the browser. A configured `PRICING_BASE_URL` is trusted configuration and can select a remote server. The current viewer narrative is a deterministic template; no viewer model annotation is implemented.

## Optional Slack acknowledgement

Starting `integrations/slack/app.py` connects to Slack. Configure an exact channel ID in `DEAL_ROOM_CHANNEL` and comma-separated allowed user IDs in `DEALDESK_SLACK_REVIEWERS`. Missing reviewer/channel configuration fails closed. Callback handling checks the allowed user, exact posted channel/message, known review and pending state. A file lock and atomic replacement serialize local review-state writes, including duplicate callbacks. Use one local filesystem for this state; it is not a distributed database.

The buttons acknowledge a review or request changes. They do not approve, release or send a quote. The local verdict is recorded before attempting Slack's display update; if that update fails, the local decision remains final and the display can be stale. Do not erase local state to retry a decision. No deal IDs, prices or margins are sent in the review card or normal acknowledgement logs, but Slack receives the opaque ID and interaction metadata. Keep tokens and `integrations/slack/runtime/` private.

## Evidence and checks

Raw socket captures now default to `data/runtime/evidence/egress_raw.log`, which is ignored. The previous raw log was removed from the current tree; it remains in Git history. Review a sanitized summary before publishing it. Sampling network sockets or seeing a clean secret scan does not prove that all traffic or secrets were found.

The full GB10 demo with networking switched off remains outstanding in [the offline checklist](../proof/OFFLINE_TEST.md). Do not disable an owner's networking, change a firewall, rotate credentials or alter a model/container configuration as an incidental demo step.
