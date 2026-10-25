# SETUP_LOG — Dell Pro Max GB10 (hackathon)

Started 2026-10-25. Owner: Suhas (local agent platform lead). Rule: all inference runs locally.

## Notes / deviations from the task
- **PLAN.md not found.** Searched `~/dealdesk` and `~` (depth 4) and the SSD. Nothing read for context yet.
- **No zip files on the SSD.** It holds one tar archive (`hackathon-complete.tar`), which I extracted instead.
- **SSD was already auto-mounted read-write** by the desktop (GNOME) at `/media/dell/suhasSSD`. I did not remount it (that needs sudo) and did not write anything to it. Only read operations were used (`ls`, `find`, `du`, `tar -t`, `tar -x` reading from it).
- No sudo commands were run.

## 1. System report
| Item | Value |
|---|---|
| OS | Ubuntu 24.04.5 LTS (Noble), kernel 7.0.0-1019-nvidia |
| CPU | aarch64 (ARM64), 20 cores: Cortex-X925 + Cortex-A725 |
| GPU | NVIDIA GB10, driver 580.178.04, CUDA 13.0. Unified memory: `nvidia-smi` shows "Not Supported" for GPU memory, so the GPU shares system RAM |
| RAM | 121 GiB total, ~115 GiB available; 15 GiB swap |
| Internal disk | `/dev/nvme0n1p2` ext4 at `/`: 3.6 T, 3.4 T free (73 G used after extraction) |
| External SSD | `/dev/sda2` exFAT "suhasSSD" (USB) at `/media/dell/suhasSSD`: 1.9 T, 1.8 T free |
| docker | 29.6.2 installed |
| ollama | **not installed** |
| python3 | 3.12.3 |
| node | **not installed** (npm also missing) |

## 2. External SSD (`lsblk`)
```
sda     1.8T disk  usb
├─sda1  200M vfat  EFI
└─sda2  1.8T exfat suhasSSD  /media/dell/suhasSSD   (rw, auto-mounted, uid=1000)
```
Contents: `hackathon-complete.tar` (39,639,921,664 bytes = 39.6 GB), a loose `hackathon/` folder, and macOS metadata (`._*`, `.Spotlight-V100`, `.fseventsd`).

The loose `hackathon/` folder is a **broken copy**. exFAT can't store symlinks, so the HF cache snapshots are missing. For example, `Qwen3.6-35B-A3B-NVFP4/snapshots/<rev>/` is empty and `refs/` is empty. **Use the tar, not the folder.**

## 3. Space check
Archive 39.6 GB, so ~2x is 79 GB needed. Internal drive had 3.4 T free. OK.

## 4. Extraction
```
mkdir -p ~/models && cd ~/models
tar -xf /media/dell/suhasSSD/hackathon-complete.tar --exclude='._*' --exclude='*/._*'
```
- Took 38 s, exit 0. Result: `~/models/hackathon/` (37 G).
- Verified with `sha256sum -c SHA256SUMS.txt`: **all 137 files OK**. No broken symlinks.

Layout of `~/models/hackathon/`:
- `hf-cache/hub/`: Hugging Face cache with the 3 models below. Use it via `HF_HOME=~/models/hackathon/hf-cache` (or mount it into the container at `/root/.cache/huggingface`).
- `images/vllm-26.05-arm64.tar` (9.6 GB): Docker image `nvcr.io/nvidia/vllm:26.05.post1-py3` for arm64. Load with `docker load -i` (not done yet).
- `vllm-flags.txt`: NVIDIA NemoClaw serving flags for Qwen3.6 (tool parser `qwen3_coder`, reasoning parser `qwen3`, MTP speculative decoding, port 8000).
- `requirements.txt` (openai, sentence-transformers, pymupdf, arxiv, biopython, slack-bolt, rapidfuzz, numpy), `slack-manifest.yaml` ("Stale Check" bot, socket mode), `evidence-check.md`, `papers/`, `vault/`, `archive/`, `private-source/` (project data).

## 5. Models
All three are **Hugging Face safetensors folders** (HF hub cache layout). None are GGUF or Ollama blobs, so they're meant for vLLM / transformers, not Ollama or llama.cpp.

| Model | Size on disk | Format / quant | What it is | Tool calling |
|---|---|---|---|---|
| `nvidia/Qwen3.6-35B-A3B-NVFP4` | 22 G (3 shards) | safetensors, NVIDIA ModelOpt mixed NVFP4/FP8, FP8 KV cache | MoE, 35B total / ~3B active, 256 experts, 40 layers, 262k context. Arch `Qwen3_5MoeForConditionalGeneration` (has vision/video preprocessors, so multimodal) | **Yes.** Chat template has tool_call blocks. vLLM: `--enable-auto-tool-choice --tool-call-parser qwen3_coder`. Main agent model. |
| `nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8` | 5.0 G (2 shards) | safetensors, ModelOpt FP8 | Hybrid Mamba-Transformer (`nemotron_h`), 4B, 42 layers, 262k context. Ships custom code + `nano_v3_reasoning_parser.py` (needs `--trust-remote-code`) | **Yes.** Chat template has tool_call support. Fast/small fallback or router model. |
| `Qwen/Qwen3-Embedding-0.6B` | 1.2 G | safetensors (BF16), sentence-transformers config | Text embedding model, 1024-dim, 32k context | **No.** Embeddings only (RAG / similarity), not a chat model. |

## Docker access (resolved)
- User `dell` was not in the `docker` group ("permission denied ... docker.sock").
- Suhas ran `sudo usermod -aG docker dell` in a separate terminal (the `!` prompt can't read a sudo password).
- Until the next login, docker commands run through `sg docker -c "..."`. After logging out and back in, plain `docker` works.

## Task 2: Model server (vLLM + Qwen3.6), 2026-10-25
- `docker ps -a` showed no containers, so there was nothing to restart.
- `docker images` was empty, so I ran `docker load -i ~/models/hackathon/images/vllm-26.05-arm64.tar`, which loaded `nvcr.io/nvidia/vllm:26.05.post1-py3` (vLLM 0.21.0).
- GPU in containers: NVIDIA Container Toolkit 1.20.1 with a CDI spec at `/var/run/cdi/nvidia.yaml`, attached with `--device nvidia.com/gpu=all`.
- Start script: `~/dealdesk/scripts/start_qwen.sh`. It recreates container `vllm-qwen`:
  - `docker run -d --restart unless-stopped`; docker/containerd are enabled at boot, so it survives tmux closing and reboots.
  - `-p 127.0.0.1:8000:8000`: localhost only (`ss` confirms it listens on 127.0.0.1:8000 only).
  - `-v ~/models/hackathon/hf-cache/hub:/models:ro`: model folder is **read-only** (verified with `docker inspect`, RW=false).
  - `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`: no downloads, no cloud.
  - All flags and env vars from `vllm-flags.txt`, including `--enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3`, MTP speculative decoding, fp8 KV cache, 131k context.
  - Served model names: `qwen3.6-35b-a3b` and `nvidia/Qwen3.6-35B-A3B-NVFP4`.
- Startup timeline: container started 15:00:17, weights loaded in 27 s (21.9 GiB), KV cache 78.6 GiB (~5.9M tokens), CUDA graphs captured. **Ready at 15:03:41 (~3.5 min).** No errors and no restarts. The Nemotron fallback was not needed.
- `curl -s http://127.0.0.1:8000/v1/models` lists both names.
- Tool-call test: `python3 scripts/test_toolcall.py qwen3.6-35b-a3b` with a fake `get_price(deal_id)` tool. The prompt "What's the price of deal D-1042?" returned `finish_reason=tool_calls` and `get_price {"deal_id": "D-1042"}`. **PASS** in 2.6 s.

Useful commands:
```
docker logs -f vllm-qwen                     # watch server logs
docker restart vllm-qwen                     # restart (~3.5 min to ready)
~/dealdesk/scripts/start_qwen.sh             # recreate from scratch
python3 ~/dealdesk/scripts/test_toolcall.py  # tool-call smoke test
```

## Still open
- PLAN.md has still not arrived in `~/dealdesk/`.
- node / ollama not installed (only needed if PLAN.md asks).

## Task 3: GitHub CLI, 2026-10-25
- `gh` was not installed (git 2.43.0 was).
- Installed **gh 2.103.2** without sudo: downloaded the official `gh_2.103.2_linux_arm64.tar.gz` from github.com/cli/cli releases, verified its SHA256 against `gh_2.103.2_checksums.txt` (OK), and copied the binary to `~/.local/bin/gh` (already on PATH), plus man pages to `~/.local/share/man/man1`.
- Not logged in yet. Suhas will run `gh auth login` (account `suhasrahul`) in a separate terminal.
- Target repo: https://github.com/ovevayrus/dealdesk-local

## Task 4: App integration, 2026-10-25
- Repo moved to `~/dealdesk-local` (was `~/dealdesk/dealdesk-local`). It has no `main` branch; the team default is `develop`. Pulled `develop` and merged it into `suhas/platform` (clean).
- **Port fix:** the DealDesk app owns 127.0.0.1:8000, so vLLM now publishes on **127.0.0.1:8001** (`scripts/start_qwen.sh`, `--restart unless-stopped`). Container recreated 15:56:44, ready 16:00:06. `ss -tlnp` shows only 127.0.0.1:8000 (app) and 127.0.0.1:8001 (vLLM).
- venv `.venv` (Python 3.12.3): `pip install -r requirements.txt`, `seed_demo_data.py --check` OK (10 documents, 51 passages), `pytest` **77 passed**.
- App runs in tmux session `dealdesk`, window `app`: `.venv/bin/python -m dealdesk`.
- `.env` (git-ignored): `DEALDESK_MODE=loca- **Fix (after a reboot, 16:12):** vLLM came back by itself (`--restart unless-stopped`); the app was restarted in tmux `dealdesk:app`. `dealdesk/llm.py` now sends `chat_template_kwargs: {"enable_thinking": false}`, with a new test `test_local_model_chat_disables_thinking` (fails without the fix). pytest: **78 passed**. Chat "Can we offer $136,000?" now returns `mode: local_model` from `qwen3.6-35b-a3b`.

## Task 5: OpenClaw + dealdesk-local skill, 2026-10-25
- Node.js **v24.22.1** (official linux-arm64 tarball, SHA256 verified) in `~/.local/opt`, symlinked into `~/.local/bin`; npm prefix `~/.local`. No sudo.
- **OpenClaw 2026.9.34** (`extended-stable` channel) via `npm install -g`. npm 11 skipped package install scripts; nothing needed them so far.
- `openclaw setup --baseline`, `openclaw telemetry off`. Config `~/.openclaw/openclaw.json`:
  - `models.mode: "replace"`: only configured providers exist, no built-in cloud catalog.
  - single provider `vllm-local` → `http://127.0.0.1:8001/v1` (`openai-completions`, dummy key, `allowPrivateNetwork: true`), model `qwen3.6-35b-a3b`.
  - `agents.defaults.model: {primary: "vllm-local/qwen3.6-35b-a3b", fallbacks: []}`, `utilityModel` same; `decisionModel` unset (disabled).
  - `openclaw models list` shows only `vllm-local/qwen3.6-35b-a3b`.
- Skill copied to `~/.openclaw/workspace/skills/dealdesk-local/` → `openclaw skills info dealdesk-local`: Ready, visible to model.
- Test: `openclaw agent --local --agent main -m "Use dealdesk-local to check whether we can offer $136,000"` took 17 s. The agent called `price_deal` via curl (one exec retry after a bad `timeout` parameter). `/api/status` → `external_agent.tool_calls_observed: 1, last_caller: openclaw`. vLLM `/metrics` confirms the requests were served locally. All figures in the answer match tool fields (offer 136000.00, discount 15.00%, stress margin 28.24%, floor 130133.34, director approval required, release not allowed).
- Note: two later checks with `python -m dealdesk tool price_deal` logged as `cli-agent` and overwrote `last_caller`. Re-test 16:39 with no CLI calls afterwards: `/api/status` → `tool_calls_observed: 4, last_caller: openclaw`. The agent still does some arithmetic of its own (e.g. "$5,866.66 above the floor", "$24,000 off") even though the skill says to copy numbers only.
- `proof/capture_egress.py`: stdlib egress sampler (host `ss` + vLLM container `/proc/<pid>/net`) that flags connections to known cloud model-provider IPs.

## Task 6: Skill rule fix and proof/, 2026-10-25
- `SKILL.md`: added a rule against computing any new number (differences, sums, "amount off", ratios) and a note that `exec` takes no `timeout` parameter. Synced to `~/.openclaw/workspace/skills/`.
- Re-test (16:45): same prompt, 15.7 s, no exec retry. Every figure in the answer is a `price_deal` field (`discount_amount` 24000.00 included); the "above the floor" difference is gone. The only reformatting is cost lines written as "$60k" for 60000.00.
- vLLM usage telemetry: a capture at 16:47 showed the container connected to `stats.vllm.ai`. Added `VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1` to `start_qwen.sh`, recreated the container (ready 16:56:05).
- Capture 16:56–17:06 with "Can we offer $136,000?" sent to `/api/chat` at 17:02:44: reply `mode: local_model` in 2.6 s, no model-provider or other outside connections from the app or vLLM.
- `proof/`: `vllm_command.txt`, `openclaw.json` (apiKey redacted), `NETWORK_SUMMARY.md` + `egress_raw.log`, `OFFLINE_TEST.md`.
