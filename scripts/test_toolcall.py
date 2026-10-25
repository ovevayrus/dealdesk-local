#!/usr/bin/env python3
"""Quick tool-call smoke test against the local vLLM server (no cloud)."""
import json
import os
import sys
import urllib.request

BASE = os.environ.get("VLLM_BASE_URL", "http://127.0.0.1:8001/v1")

models = json.load(urllib.request.urlopen(f"{BASE}/models", timeout=10))
model = sys.argv[1] if len(sys.argv) > 1 else models["data"][0]["id"]

tools = [{
    "type": "function",
    "function": {
        "name": "get_price",
        "description": "Get the current price for a deal by its ID.",
        "parameters": {
            "type": "object",
            "properties": {"deal_id": {"type": "string", "description": "Deal ID, e.g. D-1042"}},
            "required": ["deal_id"],
        },
    },
}]

body = {
    "model": model,
    "messages": [{"role": "user", "content": "What's the price of deal D-1042?"}],
    "tools": tools,
    "tool_choice": "auto",
    "max_tokens": 1024,
}
req = urllib.request.Request(f"{BASE}/chat/completions", data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json"})
resp = json.load(urllib.request.urlopen(req, timeout=300))
msg = resp["choices"][0]["message"]
calls = msg.get("tool_calls") or []
print("model:", model)
print("finish_reason:", resp["choices"][0]["finish_reason"])
for c in calls:
    print("tool_call:", c["function"]["name"], c["function"]["arguments"])
if not calls:
    print("NO TOOL CALL. content:", (msg.get("content") or "")[:500])
    sys.exit(1)
args = json.loads(calls[0]["function"]["arguments"])
ok = calls[0]["function"]["name"] == "get_price" and args.get("deal_id") == "D-1042"
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
