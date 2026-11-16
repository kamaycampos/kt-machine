// THE INSTANT ANSWER (16 Nov 2026). Kamay: "either make the built-in IG work, or ... instant".
// Meta's own comment rule never fired on KT, and the bot in pulse.yml has to LOOK (every 5 s) and is
// only shown the comments Instagram lists for it. This is the other way in, the one ManyChat-type
// tools use: Meta PUSHES each new comment here the moment it is made (webhooks, object
// "instagram", field "comments"), and this answers it with the same two calls the bot makes -
// one private reply with the link, one public "check your messages".
//
// The bot stays on as the net. Two answers to one comment cannot happen: Meta accepts ONE private
// reply per comment, this records every comment id it handled, and the bot skips a comment the
// account already answered in public.
//
// Settings (set at deploy, never in this file): VERIFY_TOKEN, APP_SECRET, PAGE_ID, PAGE_TOKEN,
// IG_USER_ID, KEYWORDS ("WISH,MONEY,BRAIN,KT"), DM_MESSAGE (the whole message, link included),
// PUBLIC_TEXT (optional), DRY ("1" = answer nothing, only record).
const G = "https://graph.facebook.com/v21.0";
const PUBLIC_DEFAULT = "Just sent it to you - check your messages \u{1F4E9}";

export function matched(text: string, kws: string[]): string | null {
  // same rule as dm_reply.matched(): a whole word, any case, stretched letters, plural, spaced out
  const up = (text || "").toUpperCase();
  for (const k of kws) {
    const gap = k.length >= 4 ? "[\\W_]{0,2}" : "";
    const body = [...k].map((ch) => ch.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "+").join(gap);
    if (new RegExp("(?<![A-Z0-9])" + body + "(?:'?S|ES)?(?![A-Z0-9])").test(up)) return k;
  }
  return null;
}

async function signed(secret: string, body: string, header: string | null): Promise<boolean> {
  if (!header || !header.startsWith("sha256=")) return false;
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const mac = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(body)));
  const hex = [...mac].map((b) => b.toString(16).padStart(2, "0")).join("");
  const want = header.slice(7);
  if (hex.length !== want.length) return false;
  let diff = 0;
  for (let i = 0; i < hex.length; i++) diff |= hex.charCodeAt(i) ^ want.charCodeAt(i);
  return diff === 0;
}

type Env = (k: string) => string | undefined;
type Fetch = typeof fetch;

export async function handle(req: Request, env: Env, kv: Deno.Kv, f: Fetch = fetch): Promise<Response> {
  const url = new URL(req.url);
  if (req.method === "GET") {
    // Meta's one-time handshake when the address is saved in the app
    if (url.searchParams.get("hub.mode") === "subscribe" &&
        url.searchParams.get("hub.verify_token") === env("VERIFY_TOKEN") && env("VERIFY_TOKEN")) {
      return new Response(url.searchParams.get("hub.challenge") ?? "", { status: 200 });
    }
    if (url.pathname === "/health") {                    // counts only, no names, no words
      const n = (await kv.get<number>(["count", "sent"])).value ?? 0;
      const last = (await kv.get<string>(["last", "event"])).value ?? null;
      return Response.json({ ok: true, sent: n, last_event: last });
    }
    return new Response("not found", { status: 404 });
  }
  if (req.method !== "POST") return new Response("no", { status: 405 });
  const raw = await req.text();
  if (!(await signed(env("APP_SECRET") ?? "", raw, req.headers.get("x-hub-signature-256")))) {
    return new Response("bad signature", { status: 401 });   // not from Meta: ignored
  }
  let data: any;
  try { data = JSON.parse(raw); } catch { return new Response("ok"); }
  const kws = (env("KEYWORDS") ?? "").split(",").map((k) => k.trim().toUpperCase()).filter(Boolean);
  const me = new Set([env("IG_USER_ID"), env("PAGE_ID")]);
  await kv.set(["last", "event"], new Date().toISOString());
  for (const entry of data?.entry ?? []) {
    for (const ch of entry?.changes ?? []) {
      if (ch?.field !== "comments") continue;
      const v = ch.value ?? {};
      const cid = String(v.id ?? "");
      if (!cid || v.parent_id) continue;                 // a reply under a comment is never an ask
      if (me.has(String(v.from?.id ?? ""))) continue;    // our own comments
      const kw = matched(String(v.text ?? ""), kws);
      if (!kw) continue;
      // first one to claim the comment id answers it; a repeat delivery finds it taken
      const claim = await kv.atomic().check({ key: ["c", cid], versionstamp: null })
        .set(["c", cid], { at: new Date().toISOString(), kw, media: v.media?.id ?? "" },
          { expireIn: 30 * 24 * 3600 * 1000 }).commit();
      if (!claim.ok) continue;
      if (env("DRY") === "1") continue;
      let state = "sent";
      try {
        const r = await f(`${G}/${env("PAGE_ID")}/messages?access_token=${encodeURIComponent(env("PAGE_TOKEN") ?? "")}`, {
          method: "POST", headers: { "content-type": "application/json" },
          body: JSON.stringify({ recipient: { comment_id: cid }, message: { text: env("DM_MESSAGE") ?? "" } }),
        });
        const j = await r.json().catch(() => ({}));
        if (j?.error) throw new Error(String(j.error.message ?? "send failed").slice(0, 200));
        await f(`${G}/${cid}/replies?access_token=${encodeURIComponent(env("PAGE_TOKEN") ?? "")}` +
          `&message=${encodeURIComponent(env("PUBLIC_TEXT") || PUBLIC_DEFAULT)}`, { method: "POST" }).catch(() => null);
        const n = (await kv.get<number>(["count", "sent"])).value ?? 0;
        await kv.set(["count", "sent"], n + 1);
      } catch (e) {
        // it did not go out: free the comment so the 5-second bot answers it
        state = "failed: " + (e instanceof Error ? e.message : "error");
        await kv.delete(["c", cid]);
      }
      await kv.set(["log", Date.now(), cid], { kw, state }, { expireIn: 30 * 24 * 3600 * 1000 });
    }
  }
  return new Response("ok");                             // always fast: Meta re-sends on anything else
}

if (import.meta.main) {
  const kv = await Deno.openKv();
  Deno.serve((req) => handle(req, (k) => Deno.env.get(k), kv));
}
