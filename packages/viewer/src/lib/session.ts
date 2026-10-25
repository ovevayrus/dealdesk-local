import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import type { Actor, ActorRole, Classification } from "@dealdesk/contracts";

function findWorkspaceRoot(): string {
  let cur = dirname(fileURLToPath(import.meta.url));
  for (let i = 0; i < 6; i++) {
    if (existsSync(resolve(cur, "pnpm-workspace.yaml"))) {
      return cur;
    }
    const parent = dirname(cur);
    if (parent === cur) break;
    cur = parent;
  }
  return process.cwd();
}

let cachedActors: Actor[] | null = null;

export function getActors(): Actor[] {
  if (!cachedActors) {
    const actorsFile = resolve(findWorkspaceRoot(), "packages/viewer/fixtures/actors.json");
    const raw = readFileSync(actorsFile, "utf-8");
    cachedActors = JSON.parse(raw);
  }
  return cachedActors!;
}

export function parseCookies(cookieHeader: string | null | undefined): Record<string, string> {
  if (!cookieHeader) return {};
  const cookies: Record<string, string> = {};
  for (const part of cookieHeader.split(";")) {
    const [key, ...vals] = part.trim().split("=");
    if (key) {
      cookies[key.trim()] = vals.join("=").trim();
    }
  }
  return cookies;
}

export function getActor(request?: Request): Actor {
  const actors = getActors();
  let actorId: string | null = null;

  if (request) {
    const cookieHeader = request.headers.get("cookie");
    const cookies = parseCookies(cookieHeader);
    if (cookies["dd_actor"]) {
      actorId = cookies["dd_actor"];
    }
  }

  if (!actorId && process.env.DEALDESK_DEV_ACTOR) {
    actorId = process.env.DEALDESK_DEV_ACTOR;
  }

  if (actorId) {
    const found = actors.find((a) => a.userId === actorId);
    if (found) return found;
  }

  return actors[0];
}

export function getAllowedClassifications(role: ActorRole): Classification[] {
  switch (role) {
    case "seller":
      return ["public", "internal"];
    case "manager":
    case "admin":
      return ["public", "internal", "restricted"];
    default:
      return ["public"];
  }
}

export function checkAccountScope(actor: Actor, accountId: string): boolean {
  if (actor.role === "admin" || actor.accountIds.includes("*")) {
    return true;
  }
  return actor.accountIds.includes(accountId);
}
