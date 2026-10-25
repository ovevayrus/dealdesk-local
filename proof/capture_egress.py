#!/usr/bin/env python3
"""Sample outbound connections while a DealDesk question runs, then summarize them.

Every 0.5 s it records:
  - host sockets from `ss -tunpH` (process names for sockets owned by this user)
  - sockets inside the vLLM container's network namespace (read from /proc/<pid>/net/*;
    the container's sockets do not appear in the host's `ss`)

Afterwards it lists every non-loopback peer, grouped by owner, and checks it against
the resolved addresses of well-known cloud model providers.

Usage: python3 proof/capture_egress.py [seconds] [raw_log] [summary_md]
Stdlib only, no sudo.
"""
import datetime as dt
import ipaddress
import socket
import subprocess
import sys
import time
from collections import defaultdict

SECONDS = int(sys.argv[1]) if len(sys.argv) > 1 else 120
RAW = sys.argv[2] if len(sys.argv) > 2 else "proof/egress_raw.log"
SUMMARY = sys.argv[3] if len(sys.argv) > 3 else "proof/EGRESS_SUMMARY.md"
CONTAINER = "vllm-qwen"
# Processes that make up the demo: the DealDesk app, vLLM, and OpenClaw (node).
APP_OWNERS = {"python", "vllm-container", "node", "openclaw"}
# Development tools running on the machine while we work, listed on their own.
DEV_TOOLS = {"claude": "development tool, not part of the DealDesk runtime"}

PROVIDER_HOSTS = [
    "api.openai.com", "api.anthropic.com", "generativelanguage.googleapis.com",
    "aiplatform.googleapis.com", "integrate.api.nvidia.com", "api.nvcf.nvidia.com",
    "api.mistral.ai", "api.groq.com", "openrouter.ai", "api.together.xyz",
    "api.cohere.com", "api.fireworks.ai", "api.deepseek.com", "api.x.ai",
    "api.perplexity.ai", "huggingface.co", "router.huggingface.co",
    "api-inference.huggingface.co", "bedrock-runtime.us-east-1.amazonaws.com",
    "openai.azure.com",
]
# Non-provider telemetry endpoints worth flagging too.
TELEMETRY_HOSTS = ["stats.vllm.ai"]


def resolve(hosts):
    out = {}
    for h in hosts:
        try:
            for info in socket.getaddrinfo(h, 443, proto=socket.IPPROTO_TCP):
                out[info[4][0]] = h
        except OSError:
            pass
    return out


def container_pid():
    try:
        return subprocess.check_output(
            ["docker", "inspect", "-f", "{{.State.Pid}}", CONTAINER], text=True).strip()
    except Exception:
        return None


def decode_proc_addr(hexaddr):
    ip_hex, port_hex = hexaddr.split(":")
    raw = bytes.fromhex(ip_hex)
    if len(raw) == 4:
        ip = ipaddress.IPv4Address(raw[::-1])
    else:  # IPv6: four little-endian 32-bit words
        ip = ipaddress.IPv6Address(b"".join(raw[i:i + 4][::-1] for i in range(0, 16, 4)))
        if ip.ipv4_mapped:
            ip = ip.ipv4_mapped
    return str(ip), int(port_hex, 16)


def container_sockets(pid):
    rows = []
    for proto in ("tcp", "tcp6", "udp", "udp6"):
        try:
            lines = open(f"/proc/{pid}/net/{proto}").read().splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            f = line.split()
            rip, rport = decode_proc_addr(f[2])
            if rport == 0:
                continue  # listening / unconnected
            lip, lport = decode_proc_addr(f[1])
            if rip == lip:
                continue  # vLLM worker processes talking to each other inside the container
            rows.append((proto, f"{lip}:{lport}", rip, rport, "vllm-container"))
    return rows


def host_sockets():
    rows = []
    out = subprocess.run(["ss", "-tunpH"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        f = line.split()
        if len(f) < 6:
            continue
        peer = f[5]
        rip, _, rport = peer.rpartition(":")
        rip = rip.strip("[]").split("%")[0]
        proc = "unattributed (not owned by this user)"
        if len(f) > 6 and 'users:(("' in f[6]:
            proc = f[6].split('"')[1]
        rows.append((f[0], f[4], rip, int(rport or 0), proc))
    return rows


def is_local(ip):
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return a.is_loopback or a.is_unspecified


def main():
    providers = resolve(PROVIDER_HOSTS)
    telemetry = resolve(TELEMETRY_HOSTS)
    cpid = container_pid()
    seen = defaultdict(int)  # (owner, ip, port) -> samples
    start = dt.datetime.now().astimezone()
    print(f"Capturing for {SECONDS}s. Ask the question in the app now.", flush=True)
    with open(RAW, "w") as log:
        log.write(f"# capture start {start.isoformat()}  container_pid={cpid}\n")
        end = time.time() + SECONDS
        while time.time() < end:
            ts = dt.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            rows = host_sockets() + (container_sockets(cpid) if cpid else [])
            for proto, local, rip, rport, owner in rows:
                if owner in APP_OWNERS:
                    log.write(f"{ts} {owner:<40} {proto:<5} {local:<28} -> {rip}:{rport}\n")
                if not is_local(rip):
                    seen[(owner, rip, rport)] += 1
            time.sleep(0.5)
    stop = dt.datetime.now().astimezone()

    def label(ip):
        if ip in providers:
            return f"**MODEL PROVIDER: {providers[ip]}**"
        if ip in telemetry:
            return f"telemetry: {telemetry[ip]}"
        return ""

    hits = [k for k in seen if k[1] in providers]
    app_hits = [k for k in hits if k[0] in APP_OWNERS]
    with open(SUMMARY, "w") as s:
        s.write("# Egress capture summary\n\n")
        s.write(f"- Window: {start:%Y-%m-%d %H:%M:%S} to {stop:%H:%M:%S %Z} ({SECONDS}s, 0.5s sampling)\n")
        s.write(f"- Host sockets: `ss -tunpH`. vLLM container sockets: `/proc/{cpid}/net/{{tcp,tcp6,udp,udp6}}`\n")
        s.write(f"- Provider addresses checked: {len(providers)} IPs from {len(PROVIDER_HOSTS)} hostnames "
                f"({', '.join(PROVIDER_HOSTS)})\n")
        s.write(f"- Raw log: `{RAW}`\n\n")
        verdict = "NONE" if not app_hits else f"{len(app_hits)} FOUND"
        s.write(f"**Model-provider connections from the DealDesk app, vLLM, or OpenClaw: {verdict}**\n\n")
        s.write("## Demo processes (DealDesk app, vLLM container, OpenClaw)\n\n")
        s.write("| Owner | Remote | Samples | Note |\n|---|---|---|---|\n")
        app_rows = sorted(k for k in seen if k[0] in APP_OWNERS)
        for owner, ip, port in app_rows:
            s.write(f"| {owner} | {ip}:{port} | {seen[(owner, ip, port)]} | {label(ip)} |\n")
        if not app_rows:
            s.write("| (none) | only 127.0.0.1 traffic | | |\n")
        s.write("\n## Development tools (not part of the DealDesk runtime)\n\n")
        s.write("| Owner | Distinct peers | Provider matches | Note |\n|---|---|---|---|\n")
        dev = defaultdict(set)
        for owner, ip, port in seen:
            if owner in DEV_TOOLS:
                dev[owner].add((ip, port))
        for owner, peers in sorted(dev.items()):
            m = sorted({providers[ip] for ip, _ in peers if ip in providers})
            s.write(f"| {owner} | {len(peers)} | {', '.join(m) or '-'} | {DEV_TOOLS[owner]} |\n")
        if not dev:
            s.write("| (none seen) | | | |\n")
        s.write("\n## Other processes on the machine (not part of the demo)\n\n")
        s.write("Peers are not listed, only counts and any provider matches.\n\n")
        s.write("| Owner | Distinct peers | Provider matches |\n|---|---|---|\n")
        others = defaultdict(set)
        for owner, ip, port in seen:
            if owner not in APP_OWNERS and owner not in DEV_TOOLS:
                others[owner].add((ip, port))
        for owner, peers in sorted(others.items()):
            m = sorted({providers[ip] for ip, _ in peers if ip in providers})
            s.write(f"| {owner} | {len(peers)} | {', '.join(m) or '-'} |\n")
    print(open(SUMMARY).read())


if __name__ == "__main__":
    main()
