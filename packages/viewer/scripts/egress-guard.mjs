// Preload that hard-fails any non-loopback network activity, so the offline
// claim is proven by the process refusing egress rather than by inspection.
// Exits non-zero if anything was blocked, so the check cannot pass silently.
import net from "node:net";
import dns from "node:dns";
import dnsPromises from "node:dns/promises";

const LOOPBACK_HOST = /^(127\.\d{1,3}\.\d{1,3}\.\d{1,3}|::1|\[::1\]|0:0:0:0:0:0:0:1|localhost)$/i;
const violations = [];
let reported = false;

function isLoopbackHost(host) {
  return LOOPBACK_HOST.test(String(host ?? "localhost"));
}

function isLoopbackAddress(address) {
  const a = String(address).replace(/^\[|\]$/g, "").replace(/^::ffff:/i, "");
  return LOOPBACK_HOST.test(a) || a === "::1";
}

function violation(kind, target) {
  const entry = `${kind} -> ${target}`;
  violations.push(entry);
  console.error(`[egress-guard] BLOCKED ${entry}`);
  return new Error(`egress-guard: non-loopback ${entry}`);
}

function report() {
  if (reported) return;
  reported = true;
  console.error(`[egress-guard] violations=${violations.length}`);
  for (const v of violations) console.error(`[egress-guard] ${v}`);
}

// --- TCP -------------------------------------------------------------------
// The supplied hostname is checked before connecting, and the address the
// resolver actually selected is checked too, so a loopback name backed by a
// custom lookup cannot reach an external host.
const connect = net.Socket.prototype.connect;
net.Socket.prototype.connect = function (...args) {
  const opts = args[0] && typeof args[0] === "object" ? args[0] : null;
  if (opts?.path) return connect.apply(this, args); // unix socket

  let host, port;
  if (opts) {
    host = opts.host;
    port = opts.port;
  } else {
    port = args[0];
    host = typeof args[1] === "string" ? args[1] : undefined;
  }
  host = String(host ?? "localhost");
  if (!isLoopbackHost(host)) throw violation("tcp", `${host}:${port}`);

  if (opts && typeof opts.lookup === "function") {
    const userLookup = opts.lookup;
    args[0] = {
      ...opts,
      lookup: (hostname, options, cb) =>
        userLookup(hostname, options, (err, address, family) => {
          if (!err && address && !isLoopbackAddress(address)) {
            return cb(violation("tcp-resolved", `${hostname} -> ${address}`));
          }
          return cb(err, address, family);
        }),
    };
  }

  this.once("lookup", (err, address) => {
    if (!err && address && !isLoopbackAddress(address)) {
      violation("tcp-resolved", `${host} -> ${address}`);
      this.destroy(new Error("egress-guard: resolved to a non-loopback address"));
    }
  });

  return connect.apply(this, args);
};

// --- DNS -------------------------------------------------------------------
// lookup alone is not enough: resolve4, the promise API and independent
// Resolver instances can all query externally on their own.
const DNS_METHODS = [
  "lookup", "resolve", "resolve4", "resolve6", "resolveAny", "resolveCname",
  "resolveMx", "resolveNaptr", "resolveNs", "resolvePtr", "resolveSoa",
  "resolveSrv", "resolveTxt",
];

function guardDns(target, label, style) {
  if (!target) return;
  for (const name of DNS_METHODS) {
    const original = target[name];
    if (typeof original !== "function") continue;
    target[name] = function (hostname, ...rest) {
      if (!isLoopbackHost(hostname)) {
        const err = violation("dns", `${label}.${name} ${hostname}`);
        if (style === "promise") return Promise.reject(err);
        const cb = rest.find((a) => typeof a === "function");
        if (cb) return cb(err);
        throw err;
      }
      return original.call(this, hostname, ...rest);
    };
  }
}

guardDns(dns, "dns", "callback");
guardDns(dns.Resolver?.prototype, "dns.Resolver", "callback");
guardDns(dnsPromises, "dns.promises", "promise");
guardDns(dnsPromises.Resolver?.prototype, "dns.promises.Resolver", "promise");

// --- fetch -----------------------------------------------------------------
const fetchImpl = globalThis.fetch;
globalThis.fetch = function (input, init) {
  const url = typeof input === "string" ? input : (input?.url ?? String(input));
  let host = "";
  try {
    host = new URL(url).hostname;
  } catch {}
  if (host && !isLoopbackHost(host)) return Promise.reject(violation("fetch", url));
  return fetchImpl.call(globalThis, input, init);
};

// --- verdict ---------------------------------------------------------------
process.on("exit", () => {
  report();
  if (violations.length > 0) process.exitCode = 1;
});

for (const sig of ["SIGTERM", "SIGINT"]) {
  process.on(sig, () => {
    report();
    process.exit(violations.length > 0 ? 1 : 0);
  });
}
