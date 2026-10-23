"""Link the Simkl account once (PIN flow), so the Favourites art can show what Ozzy actually watches.

1. asks Simkl for a PIN (needs the SIMKL_CLIENT_ID secret) and publishes only the short user code to the design-refs
   branch (refs/simkl/code.txt) so it can be passed on: enter it at simkl.com/pin
2. waits for the approval (up to 15 min), then stores the access token ENCRYPTED in simkl/token.enc (AES-256,
   key = the SIMKL_CLIENT_ID and MDBLIST_API_KEY secrets, which only GitHub has). The token is never printed.
usage (CI): python3 scripts/simkl_link.py
"""
import json, os, subprocess, sys, time, urllib.request

CID = os.environ["SIMKL_CLIENT_ID"].strip()
UA = {"User-Agent": "nuvio-awards", "Content-Type": "application/json"}


def get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())


def publish_code(text):
    os.makedirs("refs/simkl", exist_ok=True)
    open("refs/simkl/code.txt", "w").write(text)
    subprocess.run("git checkout -q -B design-refs && git add -f refs/simkl && git commit -q -m 'Simkl PIN' && "
                   "git push -q -f origin design-refs && git checkout -q -", shell=True, check=True)


pin = get(f"https://api.simkl.com/oauth/pin?client_id={CID}")
code = pin["user_code"]
publish_code(f"code: {code}\nenter at: {pin.get('verification_url', 'https://simkl.com/pin')}\nexpires in: {pin.get('expires_in')} s\n")
print("PIN published; waiting for approval")
token = None
for _ in range(int(min(900, pin.get("expires_in", 900)) / max(5, pin.get("interval", 5)))):
    time.sleep(max(5, pin.get("interval", 5)))
    r = get(f"https://api.simkl.com/oauth/pin/{code}?client_id={CID}")
    if r.get("result") == "OK" and r.get("access_token"):
        token = r["access_token"]
        break
if not token:
    publish_code("not approved in time - run the Simkl link workflow again\n")
    sys.exit(1)
key = CID + os.environ["MDBLIST_API_KEY"].strip()
enc = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-a", "-pass", "env:K"],
                     input=token.encode(), capture_output=True, env={**os.environ, "K": key}, check=True).stdout
os.makedirs("simkl", exist_ok=True)
open("simkl/token.enc", "wb").write(enc)
publish_code("linked - the token is stored encrypted in simkl/token.enc\n")
print("linked")
