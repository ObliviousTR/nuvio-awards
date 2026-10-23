"""Link the Simkl account once (AUTH V2 device flow), so the Favourites art can show what Ozzy actually watches.
Publishes only the short user code (and the simkl.com/pin link) to design-refs refs/simkl/code.txt, waits up to
15 minutes for the approval, then stores the tokens ENCRYPTED in simkl/token.enc. Nothing secret is printed.
needs: SIMKL_CLIENT_ID, SIMKL_CLIENT_SECRET (if Simkl asks for it), MDBLIST_API_KEY
"""
import os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import simkl_auth as S


def publish(text):
    err = S.gh_put("refs/simkl/code.txt", text.encode(), "design-refs", "Simkl link")
    if err:
        print("could not publish the status:", err)


if not S.CID:
    publish("error: the SIMKL_CLIENT_ID secret is empty or missing\n")
    sys.exit(1)
st, d = S.post("/oauth2/device", {"client_id": S.CID, "scope": "media:read"})
if st != 200 or "device_code" not in d:
    publish(f"error: HTTP {st} {d.get('error')} {S.scrub(str(d.get('error_description') or d.get('message') or ''))}\n")
    sys.exit(1)
publish(f"code: {d['user_code']}\nlink: {d.get('verification_uri_complete') or d.get('verification_uri')}\n"
        f"expires in: {d.get('expires_in')} s\n")
print("code published; waiting for approval")
wait, end = max(5, int(d.get("interval", 5))), time.time() + min(900, int(d.get("expires_in", 900)))
tok = None
while time.time() < end:
    time.sleep(wait)
    st, r = S.post("/oauth2/token", {**S.creds(), "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                                     "device_code": d["device_code"]})
    if st == 200 and "access_token" in r:
        tok = r
        break
    err = r.get("error")
    if err == "authorization_pending":
        continue
    if err == "slow_down":
        wait += 5
        continue
    publish(f"error while waiting: HTTP {st} {err} {S.scrub(str(r.get('error_description', '')))}\n")
    sys.exit(1)
if not tok:
    publish("not approved in time - run the Simkl link workflow again\n")
    sys.exit(1)
S.save(S.keep(tok))
err = S.gh_put("simkl/token.enc", open(S.FILE, "rb").read(), "main", "Simkl linked (tokens encrypted)")
if err:
    publish(f"approved, but saving the encrypted tokens failed: {err}\n")
    sys.exit(1)
publish(f"linked (scope: {tok.get('scope', '?')}) - tokens stored encrypted in simkl/token.enc\n")
print("linked")
