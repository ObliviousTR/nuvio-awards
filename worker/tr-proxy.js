// Nuvio TR proxy: sits in front of Ozzy's AIOMetadata. Every request is passed through unchanged, except that in
// catalog and meta answers Turkish productions get their own name and logo back (trmeta/map.json, built daily on
// GitHub). Posters+ posters keep their badges and only switch to the title's original-language logo.
// Only the configured AIOMetadata path is served (AIO_ORIGIN + AIO_PATH, both Worker secrets).
// If anything goes wrong while rewriting, the original answer is returned as it is.

const MAP_TTL = 3600 * 1000;
let MAP = null, MAP_AT = 0;

async function loadMap(env) {
  if (MAP && Date.now() - MAP_AT < MAP_TTL) return MAP;
  try {
    const r = await fetch(env.MAP_URL, { cf: { cacheTtl: 3600, cacheEverything: true } });
    if (r.ok) { MAP = await r.json(); MAP_AT = Date.now(); }
  } catch (e) { /* keep the old map, or none */ }
  return MAP;
}

const PP_LOGO = "original,native,english,neutral,text";

function fixPoster(url, entry, img) {
  if (!url) return url;
  try {
    const u = new URL(url);
    if (u.hostname.includes("postersplus")) {          // badge posters: same poster, Turkish logo
      u.searchParams.set("logo_priority", PP_LOGO);
      return u.toString();
    }
  } catch (e) { return url; }
  return entry[2] ? img + "w500" + entry[2] : url;     // plain posters: the Turkish poster
}

function fixMeta(m, type, map) {
  if (!m || typeof m !== "object") return false;
  const t = m.type || type;
  const entry = map.items[`${t}|${m.id}`] || (m.imdb_id && map.items[`${t}|${m.imdb_id}`]);
  if (!entry) return false;
  const img = map.img || "https://image.tmdb.org/t/p/";
  if (entry[0]) m.name = entry[0];
  if (entry[1]) m.logo = img + "w500" + entry[1];
  if (m.poster) m.poster = fixPoster(m.poster, entry, img);
  return true;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const base = env.AIO_PATH.replace(/\/+$/, "");          // e.g. /stremio/<uuid>
    if (!(url.pathname === base || url.pathname.startsWith(base + "/"))) {
      return new Response("Not found", { status: 404 });
    }
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*" } });
    }
    const upstream = env.AIO_ORIGIN.replace(/\/+$/, "") + url.pathname + url.search;
    const resp = await fetch(upstream, { method: request.method, headers: request.headers, redirect: "follow" });
    const m = url.pathname.slice(base.length).match(/^\/(catalog|meta)\/([^/]+)\//);
    if (!m || !resp.ok || !(resp.headers.get("content-type") || "").includes("json")) return resp;
    try {
      const map = await loadMap(env);
      if (!map || !map.items) return resp;
      const body = await resp.clone().json();
      let changed = false;
      if (m[1] === "meta") changed = fixMeta(body.meta, m[2], map);
      else for (const it of body.metas || []) changed = fixMeta(it, m[2], map) || changed;
      if (!changed) return resp;
      const headers = new Headers(resp.headers);
      headers.delete("content-length"); headers.delete("content-encoding"); headers.delete("etag");
      headers.set("Access-Control-Allow-Origin", "*");
      return new Response(JSON.stringify(body), { status: resp.status, headers });
    } catch (e) {
      return resp;
    }
  },
};
