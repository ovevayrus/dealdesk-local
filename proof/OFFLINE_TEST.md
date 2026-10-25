# Offline test (GB10, network off)

Goal: show that a full DealDesk quote, including the local model's reply and an OpenClaw tool
call, works with every network link on the GB10 turned off. Do this at the GB10's own keyboard
and screen, because turning off networking also cuts any SSH or remote-desktop session.

Interfaces on this machine (from `nmcli dev`): Wi-Fi `wlP9s9` (the only uplink in use),
Ethernet `enP7s7` (no cable), Tailscale `tailscale0` (rides on Wi-Fi), and `docker0` (local
bridge only).

## 1. Before you start (network still on)

Open a terminal on the GB10 and confirm everything is running:

```sh
docker ps --filter name=vllm-qwen --format '{{.Status}}'      # "Up ..."
curl -s http://127.0.0.1:8001/v1/models | grep -o qwen3.6-35b-a3b | head -1
curl -s http://127.0.0.1:8000/api/status | python3 -m json.tool | head -20
```

If the app is not running: `tmux attach -t dealdesk`, or from `~/dealdesk-local` run
`.venv/bin/python -m dealdesk`.

## 2. Turn networking off

1. Click the system menu in the top-right corner of the GNOME screen.
2. Turn on **Airplane Mode** (this turns off Wi-Fi and Bluetooth). If there is no Airplane Mode
   toggle, turn **Wi-Fi** off instead.
3. Make sure no Ethernet cable is plugged into the GB10.

Tailscale has no path out once Wi-Fi is off, so it needs no separate step.

## 3. Confirm the machine is offline

```sh
nmcli -t -f DEVICE,STATE dev        # wlP9s9 should show "unavailable" or "disconnected"
ip route                            # no "default via ..." line
ping -c 2 -W 2 1.1.1.1              # should fail: "Network is unreachable" or 100% loss
getent hosts api.openai.com || echo "DNS: no answer (expected offline)"
```

Take a photo or screenshot of this output.

## 4. Run a quote

In the browser on the GB10, open `http://127.0.0.1:8000` and ask:

> Can we offer $136,000?

Expected:
- The reply appears with the quote cards: offer 136,000.00,
  discount 15.00%, stress margin 28.24%, economic floor 130,133.34, Director approval required.
- The header shows "Local model endpoint", not "Scripted demo mode".

Then run the agent path in a terminal:

```sh
cd ~/dealdesk-local
openclaw agent --local --agent main -m 'Use dealdesk-local to check whether we can offer $136,000'
curl -s http://127.0.0.1:8000/api/status | python3 -m json.tool | grep -A4 external_agent
```

Expected: an answer in about 16 s (15.7 s measured online) with the same figures, and `last_caller: "openclaw"` with
`tool_calls_observed` one higher than before. The chat page shows a new "Local agent tool call".

Optional: run `python3 proof/capture_egress.py 60 proof/egress_offline_raw.log
proof/NETWORK_SUMMARY_OFFLINE.md` while asking the question. Offline, provider DNS names do not
resolve, so the provider list will be empty; the useful result is that every demo connection is
to `127.0.0.1`.

## 5. Record the result

Write down the time, the reply time, and pass/fail for each check in this file under
"Results", along with the screenshots.

## 6. Turn networking back on

Turn Airplane Mode off (or Wi-Fi on) from the same system menu. Check with
`ping -c 2 1.1.1.1`.

## Results

| Check | Result |
|---|---|
| Date / time | |
| `ping 1.1.1.1` fails | |
| App reply in local-model mode, figures as above | |
| App reply time | |
| OpenClaw answer, `last_caller: openclaw` | |
| Networking restored | |
