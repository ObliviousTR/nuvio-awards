// Nuvio TR proxy (v2): sits in front of Ozzy's AIOMetadata. Every request is passed through unchanged, except that
// in catalog and meta answers Turkish productions get their own name, Turkish overview and Turkish logo
// (trmeta on GitHub, rebuilt daily):
//   - a Turkish logo exists: name, overview and logo are Turkish; a Posters+ poster keeps its badges and switches to
//     the Turkish logo (logo_priority=original...)
//   - no Turkish logo: name and overview are Turkish; the English logo is dropped from the detail page so the Turkish
//     name shows as text; the poster stays as it is
// Only the configured AIOMetadata path is served (AIO_ORIGIN + AIO_PATH, both Worker secrets).
// Any problem while rewriting returns AIOMetadata's own answer untouched.

const TTL = 3600 * 1000;
let KEYS = null, KEYS_AT = 0;
const SHARDS = new Map();          // "xx" -> {at, data}

function fnv(key) {
  let h = 0x811c9dc5;
  for (const b of new TextEncoder().encode(key)) {
    h ^= b;
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

async function keys(env) {
  if (KEYS && Date.now() - KEYS_AT < TTL) return KEYS;
  try {
    const r = await fetch(env.DATA_URL + "/keys.txt", { cf: { cacheTtl: 3600, cacheEverything: true } });
    if (r.ok) { KEYS = new Set((await r.text()).split("\n")); KEYS_AT = Date.now(); }
  } catch (e) { /* keep the old set, or none */ }
  return KEYS;
}

async function entry(env, key) {
  const h = (fnv(key) % 256).toString(16).padStart(2, "0");
  let s = SHARDS.get(h);
  if (!s || Date.now() - s.at > TTL) {
    const r = await fetch(`${env.DATA_URL}/s/${h}.json`, { cf: { cacheTtl: 3600, cacheEverything: true } });
    if (!r.ok) return null;
    s = { at: Date.now(), data: await r.json() };
    SHARDS.set(h, s);
  }
  return s.data[key] || null;
}

const IMG = "https://image.tmdb.org/t/p/";
const PP_LOGO = "original,native,english,neutral,text";

function keyOf(m, type) {
  return `${m.type || type}|${m.id}`;
}

function apply(m, e, isMeta) {
  const [name, logo, , overview] = e;
  if (name) m.name = name;
  if (overview) m.description = overview;
  if (logo) {
    m.logo = IMG + "w500" + logo;
    if (m.poster) {
      try {
        const u = new URL(m.poster);
        if (u.hostname.includes("postersplus")) {
          u.searchParams.set("logo_priority", PP_LOGO);
          m.poster = u.toString();
        }
      } catch (err) { /* leave the poster */ }
    }
  } else if (m.logo) {
    delete m.logo;                 // an English logo next to a Turkish name: show the name instead
  }
}

function cors(resp) {
  const headers = new Headers(resp.headers);
  headers.delete("content-length"); headers.delete("content-encoding"); headers.delete("etag");
  headers.set("Access-Control-Allow-Origin", "*");
  return headers;
}

const PP_ORIGIN = "https://postersplus.slokker.cc";

async function posterRedirect(url, base, env) {
  const target = new URL(PP_ORIGIN + url.pathname.slice((base + "/pp").length) + url.search);
  try {
    const q = target.searchParams;
    const type = q.get("type") === "series" || q.get("type") === "tv" ? "series" : "movie";
    const set = await keys(env);
    const cands = [q.get("imdb_id"), q.get("stremio_id"), q.get("tmdb_id") && `tmdb:${q.get("tmdb_id")}`]
      .filter(Boolean).map(id => `${type}|${id}`);
    const key = set && cands.find(k => set.has(k));
    const e = key && await entry(env, key);
    if (e && e[1]) q.set("logo_priority", PP_LOGO);
  } catch (err) { /* plain redirect */ }
  return new Response(null, { status: 302, headers: { Location: target.toString(), "Cache-Control": "public, max-age=86400" } });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const base = env.AIO_PATH.replace(/\/+$/, "");
    if (!(url.pathname === base || url.pathname.startsWith(base + "/"))) {
      return new Response("Not found", { status: 404 });
    }
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*" } });
    }
    // Posters+ through the app's own custom-poster pattern: <base>/pp/<path>?<query> redirects to
    // postersplus.slokker.cc/<path>?<query>, with the Turkish logo asked for when the title is Turkish and has one
    if (url.pathname.startsWith(base + "/pp/")) return posterRedirect(url, base, env);
    const upstream = env.AIO_ORIGIN.replace(/\/+$/, "") + url.pathname + url.search;
    const resp = await fetch(upstream, { method: request.method, headers: request.headers, redirect: "follow" });
    const m = url.pathname.slice(base.length).match(/^\/(catalog|meta)\/([^/]+)\/([^/]+)\.json$|^\/(catalog)\/([^/]+)\//);
    if (!m || !resp.ok || !(resp.headers.get("content-type") || "").includes("json")) return resp;
    try {
      const set = await keys(env);
      if (!set) return resp;
      const kind = m[1] || m[4], type = m[2] || m[5];
      if (kind === "meta") {
        // a meta request names its id in the URL: no Turkish key, nothing to read
        const id = decodeURIComponent(m[3]);
        if (!set.has(`${type}|${id}`)) return resp;
        const body = await resp.clone().json();
        const e = body.meta && await entry(env, keyOf(body.meta, type));
        if (!e) return resp;
        apply(body.meta, e, true);
        return new Response(JSON.stringify(body), { status: resp.status, headers: cors(resp) });
      }
      const body = await resp.clone().json();
      const hits = (body.metas || []).filter(x => x && set.has(keyOf(x, type)));
      if (!hits.length) return resp;
      let changed = false;
      for (const x of hits) {
        const e = await entry(env, keyOf(x, type));
        if (e) { apply(x, e, false); changed = true; }
      }
      return changed ? new Response(JSON.stringify(body), { status: resp.status, headers: cors(resp) }) : resp;
    } catch (err) {
      return resp;
    }
  },
};
