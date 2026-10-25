// Preload that hard-fails any non-loopback network activity, so the offline
// claim is proven by the process refusing egress rather than by inspection.
import net from "node:net";
import dns from "node:dns";

const LOOPBACK = /^(127\.\d+\.\d+\.\d+|::1|\[::1\]|localhost)$/;
const violations = [];

function violation(kind, target) {
  const entry = `${kind} -> ${target}`;
  violations.push(entry);
  console.error(`[egress-guard] BLOCKED ${entry}`);
  return new Error(`egress-guard: non-loopback ${entry}`);
}

const connect = net.Socket.prototype.connect;
net.Socket.prototype.connect = function (...args) {
  const first = args[0];
  let host, port;
  if (first && typeof first === "object") {
    if (first.path) return connect.apply(this, args); // unix socket
    host = first.host;
    port = first.port;
  } else {
    port = first;
    host = typeof args[1] === "string" ? args[1] : undefined;
  }
  host = String(host ?? "localhost");
  if (!LOOPBACK.test(host)) throw violation("tcp", `${host}:${port}`);
  return connect.apply(this, args);
};

const lookup = dns.lookup;
dns.lookup = function (hostname, ...rest) {
  if (!LOOPBACK.test(String(hostname))) {
    const err = violation("dns", String(hostname));
    const cb = rest.find((a) => typeof a === "function");
    if (cb) return cb(err);
    throw err;
  }
  return lookup.call(dns, hostname, ...rest);
};

const fetchImpl = globalThis.fetch;
globalThis.fetch = function (input, init) {
  const url = typeof input === "string" ? input : input?.url ?? String(input);
  let host = "";
  try {
    host = new URL(url).hostname;
  } catch {}
  if (host && !LOOPBACK.test(host)) return Promise.reject(violation("fetch", url));
  return fetchImpl.call(globalThis, input, init);
};

process.on("exit", () => {
  console.error(`[egress-guard] violations=${violations.length}`);
  for (const v of violations) console.error(`[egress-guard] ${v}`);
});

for (const sig of ["SIGTERM", "SIGINT"]) {
  process.on(sig, () => {
    console.error(`[egress-guard] violations=${violations.length} (on ${sig})`);
    process.exit(0);
  });
}
