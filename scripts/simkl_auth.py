"""Simkl AUTH V2 helpers. Tokens live only ENCRYPTED in simkl/token.enc (AES-256; the key is made of GitHub secrets),
and are never printed. Access tokens last 7 days, refresh tokens 180 days (sliding), so every run refreshes and
re-saves the file; the calling workflow commits it."""
import json, os, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE = os.path.join(ROOT, "simkl", "token.enc")
CID = os.environ.get("SIMKL_CLIENT_ID", "").strip()
SECRET = os.environ.get("SIMKL_CLIENT_SECRET", "").strip()
APP = {"client_id": CID, "app-name": "nuvio-awards", "app-version": "1.0"}
UA = "nuvio-awards/1.0"


def scrub(t):
    for k in (CID, SECRET, os.environ.get("MDBLIST_API_KEY", ""), os.environ.get("TMDB_API_KEY", "")):
        if k:
            t = t.replace(k, "***")
    return t


def _key():
    return CID + os.environ["MDBLIST_API_KEY"].strip()


def save(tok):
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    enc = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-a", "-pass", "env:K"],
                         input=json.dumps(tok).encode(), capture_output=True, env={**os.environ, "K": _key()}, check=True).stdout
    open(FILE, "wb").write(enc)


def load():
    raw = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-a", "-pass", "env:K", "-in", FILE],
                         capture_output=True, env={**os.environ, "K": _key()}, check=True).stdout.decode()
    return json.loads(raw)


def post(path, data):
    """POST form data; returns (status, json body) - OAuth errors come back as 4xx with a JSON body."""
    url = f"https://api.simkl.com{path}?" + urllib.parse.urlencode(APP)
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(),
                                 headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded",
                                          "Accept": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=60)
        return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        b = e.read()
        try:
            return e.code, json.loads(b)
        except Exception:
            return e.code, {"error": "http_%d" % e.code, "error_description": scrub(b[:200].decode("utf-8", "replace"))}


def creds():
    d = {"client_id": CID}
    if SECRET:
        d["client_secret"] = SECRET
    return d


def keep(tok, old=None):
    """normalise a token response into what we store"""
    return {"access_token": tok["access_token"], "refresh_token": tok.get("refresh_token") or (old or {}).get("refresh_token"),
            "expires_at": int(time.time()) + int(tok.get("expires_in", 7 * 86400)), "scope": tok.get("scope", "")}


def access_token(force=False):
    tok = load()
    if force or tok["expires_at"] - time.time() < 2 * 86400:
        st, r = post("/oauth2/token", {**creds(), "grant_type": "refresh_token", "refresh_token": tok["refresh_token"]})
        if st != 200 or "access_token" not in r:
            raise SystemExit(f"Simkl refresh failed: HTTP {st} {r.get('error')} {scrub(str(r.get('error_description', '')))}")
        tok = keep(r, tok)
        save(tok)
    return tok["access_token"]


def get(path, tok):
    sep = "&" if "?" in path else "?"
    u = f"https://api.simkl.com{path}{sep}" + urllib.parse.urlencode(APP)
    r = urllib.request.Request(u, headers={"simkl-api-key": CID, "Authorization": "Bearer " + tok, "User-Agent": UA,
                                           "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=60).read() or b"null") or {}
