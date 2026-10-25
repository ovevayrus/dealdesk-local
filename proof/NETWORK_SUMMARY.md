# Egress capture summary

- Window: 2026-10-25 16:56:19 to 17:06:19 CDT (600s, 0.5s sampling)
- Host sockets: `ss -tunpH`. vLLM container sockets: `/proc/72276/net/{tcp,tcp6,udp,udp6}`
- Provider addresses checked: 96 IPs from 20 hostnames (api.openai.com, api.anthropic.com, generativelanguage.googleapis.com, aiplatform.googleapis.com, integrate.api.nvidia.com, api.nvcf.nvidia.com, api.mistral.ai, api.groq.com, openrouter.ai, api.together.xyz, api.cohere.com, api.fireworks.ai, api.deepseek.com, api.x.ai, api.perplexity.ai, huggingface.co, router.huggingface.co, api-inference.huggingface.co, bedrock-runtime.us-east-1.amazonaws.com, openai.azure.com)
- Raw log: `proof/egress_raw.log`

**Model-provider connections from the DealDesk app, vLLM, or OpenClaw: NONE**

## Demo processes (DealDesk app, vLLM container, OpenClaw)

| Owner | Remote | Samples | Note |
|---|---|---|---|
| vllm-container | 172.17.0.1:34928 | 121 |  |
| vllm-container | 172.17.0.1:37364 | 107 |  |
| vllm-container | 172.17.0.1:41952 | 116 |  |

## Development tools (not part of the DealDesk runtime)

| Owner | Distinct peers | Provider matches | Note |
|---|---|---|---|
| claude | 5 | api.anthropic.com | development tool, not part of the DealDesk runtime |

## Other processes on the machine (not part of the demo)

Peers are not listed, only counts and any provider matches.

| Owner | Distinct peers | Provider matches |
|---|---|---|
| firefox | 7 | - |
| unattributed (not owned by this user) | 22 | - |

## What happened during the window

- **17:02:44.99**: `POST http://127.0.0.1:8000/api/chat` with `{"message": "Can we offer $136,000?"}`
  (sent with curl on the GB10). Reply at 17:02:47.59 (2.6 s): `mode: local_model`,
  `model: qwen3.6-35b-a3b`, 15.00% discount, economic floor $130,133.34, stress margin 28.24%,
  Director approval required.
- The raw log shows the request path at that moment, all on this machine:
  `python 127.0.0.1:8000 <- client` (the app), `python 127.0.0.1:38346 -> 127.0.0.1:8001` (app to vLLM),
  and `vllm-container 172.17.0.2:8000 <- 172.17.0.1` (Docker forwarding the host's 127.0.0.1:8001
  into the container).
- `172.17.0.1` is the host's `docker0` bridge address, not an outside host. Those are the only peers
  the vLLM container had.
- `firefox` and the root-owned ("unattributed") system processes are not part of DealDesk. None of
  them connected to a model provider.
- `claude` is Claude Code, the development tool used to set up this machine. It is not part of the
  DealDesk runtime and is not needed to run the demo.

## Earlier capture (16:47–16:49): vLLM usage telemetry, now off

An earlier two-minute capture found the vLLM container holding a connection to `stats.vllm.ai`
(104.21.88.245:443) the whole time. This is vLLM's usage-statistics reporting, not model traffic.
`scripts/start_qwen.sh` now sets `VLLM_NO_USAGE_STATS=1` and `DO_NOT_TRACK=1`. The container was
recreated at 16:52 and had no outside connections in this capture.
