// deno test --unstable-kv dm/hook/main_test.ts
import { handle, matched } from "./main.ts";

const SECRET = "s3cret";
const ENV: Record<string, string> = {
  VERIFY_TOKEN: "vt", APP_SECRET: SECRET, PAGE_ID: "PG", PAGE_TOKEN: "tok", IG_USER_ID: "IGME",
  KEYWORDS: "WISH,MONEY,BRAIN,KT", DM_MESSAGE: "Hey! Thanks for commenting. Here it is: https://example.com/x",
};
const env = (k: string) => ENV[k];

async function sign(body: string, secret = SECRET) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const mac = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(body)));
  return "sha256=" + [...mac].map((b) => b.toString(16).padStart(2, "0")).join("");
}
const ev = (v: Record<string, unknown>) =>
  JSON.stringify({ object: "instagram", entry: [{ id: "IGME", time: 1, changes: [{ field: "comments", value: v }] }] });
async function post(kv: Deno.Kv, body: string, calls: string[], opt: { sig?: string; fail?: boolean } = {}) {
  const f = ((u: string | URL | Request, init?: RequestInit) => {
    calls.push(`${init?.method} ${String(u).split("?")[0]} ${init?.body ?? ""}`);
    return Promise.resolve(Response.json(opt.fail ? { error: { message: "nope" } } : { message_id: "m1", id: "r1" }));
  }) as typeof fetch;
  return await handle(new Request("https://h/", { method: "POST", body,
    headers: { "x-hub-signature-256": opt.sig ?? await sign(body) } }), env, kv, f);
}
function eq(a: unknown, b: unknown, m = "") { if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error(`${m}: ${JSON.stringify(a)} != ${JSON.stringify(b)}`); }

Deno.test("keyword matching is the bot's", () => {
  const k = ["WISH", "MONEY", "BRAIN", "KT"];
  eq(matched("Wish", k), "WISH"); eq(matched("wish please", k), "WISH"); eq(matched("moneyyy!!", k), "MONEY");
  eq(matched("m o n e y", k), "MONEY"); eq(matched("brains", k), "BRAIN"); eq(matched("brainstorm", k), null);
  eq(matched("Indeed", k), null); eq(matched("Im getting a Purple lamborghini", k), null); eq(matched("", k), null);
});

Deno.test("handshake, signature, one answer per comment, replies and own comments ignored", async () => {
  const kv = await Deno.openKv(":memory:");
  const hs = await handle(new Request("https://h/?hub.mode=subscribe&hub.verify_token=vt&hub.challenge=777"), env, kv);
  eq(await hs.text(), "777", "handshake");
  eq((await handle(new Request("https://h/?hub.mode=subscribe&hub.verify_token=bad&hub.challenge=777"), env, kv)).status, 404);

  let calls: string[] = [];
  const mel = ev({ id: "C1", text: "Wish", from: { id: "U1", username: "mel" }, media: { id: "M1" } });
  eq((await post(kv, mel, calls, { sig: "sha256=00" })).status, 401, "forged"); eq(calls.length, 0, "forged sends nothing");
  eq((await post(kv, mel, calls)).status, 200); eq(calls.length, 2, "DM + public reply");
  if (!calls[0].startsWith("POST https://graph.facebook.com/v21.0/PG/messages") || !calls[0].includes('"comment_id":"C1"')) throw new Error(calls[0]);
  if (!calls[1].startsWith("POST https://graph.facebook.com/v21.0/C1/replies")) throw new Error(calls[1]);
  await post(kv, mel, calls); eq(calls.length, 2, "Meta re-sends the same comment: no second answer");

  calls = [];
  await post(kv, ev({ id: "C2", text: "Indeed", from: { id: "U2" } }), calls);
  await post(kv, ev({ id: "C3", text: "wish", from: { id: "U3" }, parent_id: "C1" }), calls);
  await post(kv, ev({ id: "C4", text: "Comment WISH", from: { id: "IGME" } }), calls);
  eq(calls.length, 0, "no keyword / a reply / our own comment");

  // a failed send frees the comment, so the 5-second bot (or a re-send) can still answer it
  await post(kv, ev({ id: "C5", text: "MONEY", from: { id: "U5" } }), calls, { fail: true });
  eq((await kv.get(["c", "C5"])).value, null, "freed after a failure");
  const h = await (await handle(new Request("https://h/health"), env, kv)).json();
  eq(h.sent, 1, "health count");
  kv.close();
});
