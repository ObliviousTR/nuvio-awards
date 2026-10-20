"""Covers for the Favourites row, in the Spotlight style. Runs in the Spotlight workflow; skips files that exist
(--redraw to rebuild). Doctor Who keeps the user's own cover and GIF; One Pace keeps its GIF.
  One Pace:   One Piece backdrop from TMDB (textless), our text block.
  Live Sport: night stadium photo from Wikimedia Commons (free licence, credited in spotlight/art/CREDITS.md),
              LIVE badge; hover GIF = slow zoom with a pulsing LIVE dot.
"""
import io, json, os, sys, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spotlight_art as art
from spotlight import tmdb, P
from PIL import Image, ImageEnhance

COMMONS = "File:Germany and Argentina face off in the final of the World Cup 2014 -2014-07-13 (5).jpg"
ONEPACE_BACKDROP = ""  # TMDB file_path of the chosen One Piece backdrop (see onepace/candidates.jpg)
UA = {"User-Agent": "nuvio-awards (github.com/ObliviousTR/nuvio-awards)"}


def commons(title, width=1920):
    q = {"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "url|extmetadata",
         "iiurlwidth": str(width), "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl", "format": "json"}
    d = json.loads(urllib.request.urlopen(urllib.request.Request(
        "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(q), headers=UA), timeout=60).read())
    ii = next(iter(d["query"]["pages"].values()))["imageinfo"][0]
    img = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(ii["thumburl"], headers=UA), timeout=120).read()))
    meta = {k: v.get("value", "") for k, v in ii.get("extmetadata", {}).items()}
    return img, meta, ii["descriptionurl"]


def contact_sheet(imgs, path, tw=480, th=270):
    """Numbered preview of backdrop candidates (file paths in the caption file next to it)."""
    from PIL import ImageDraw
    sheet = Image.new("RGB", (4 * tw, ((len(imgs) + 3) // 4) * th), (0, 0, 0))
    d = ImageDraw.Draw(sheet)
    for i, b in enumerate(imgs):
        im = art.fetch(b["file_path"], "w780")
        if im:
            sheet.paste(art.cover_fit(im.convert("RGB"), tw, th), ((i % 4) * tw, (i // 4) * th))
        d.text(((i % 4) * tw + 8, (i // 4) * th + 8), str(i), fill=(255, 255, 0))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sheet.save(path, "JPEG", quality=80)
    open(path.replace(".jpg", ".txt"), "w").write("\n".join(f"{i} {b['file_path']}" for i, b in enumerate(imgs)))


def darken(im, b=0.6):
    return ImageEnhance.Brightness(art.cover_fit(im.convert("RGB"), art.W, art.H)).enhance(b)


def main(redraw=False):
    out = P("art", "favourites")
    # One Pace
    if redraw or not os.path.exists(f"{out}/onepace/cover.jpg"):
        imgs = (tmdb("/tv/37854/images", include_image_language="null") or {}).get("backdrops", [])
        imgs.sort(key=lambda b: (-b.get("vote_average", 0), -b.get("width", 0)))
        contact_sheet(imgs[:16], f"{out}/onepace/candidates.jpg")
        pick = [b for b in imgs if b["file_path"] == ONEPACE_BACKDROP]
        imgs = pick + [b for b in imgs if b not in pick]
        art.cover(f"{out}/onepace/cover.jpg", card="One Pace", tag="Fan re-cut", title="One Pace",
                  subtitle="One Piece · without the filler", accent="#E63946",
                  backdrop=imgs[0]["file_path"] if imgs else None)
        if imgs:
            art.backdrop(f"{out}/onepace/backdrop.jpg", imgs[0]["file_path"])
    # Live Sport
    if redraw or not os.path.exists(f"{out}/livesport/cover.jpg"):
        photo, meta, url = commons(COMMONS)
        base = darken(photo, 0.62)
        kw = dict(card="Live Sport", tag="Matches · Replays · Channels", title="Live Sport",
                  subtitle="Football · Basketball · Motorsport · Tennis · Darts", accent="#E50914")
        os.makedirs(f"{out}/livesport", exist_ok=True)
        art.live_pill(art.cover(None, base=base, **kw)).save(f"{out}/livesport/cover.jpg", "JPEG", quality=86,
                                                             optimize=True, progressive=True)
        art.cover_fit(photo.convert("RGB"), 1920, 1080).save(f"{out}/livesport/backdrop.jpg", "JPEG", quality=82)
        art.ken_burns_gif(f"{out}/livesport/hover.gif",
                          lambda t: art.live_pill(art.cover(None, base=art.zoomed(base, 0.07 * t), **kw),
                                                  glow=abs(((t * 4) % 2) - 1)))
        import re
        artist = re.sub(r"<[^>]+>", "", meta.get("Artist", "")).strip()
        open(P("art", "CREDITS.md"), "w", encoding="utf-8").write(
            "# Image credits\n\n"
            f"- **Live Sport** cover, backdrop and hover: “{COMMONS[5:]}” by {artist}, "
            f"{meta.get('LicenseShortName', '')} ({meta.get('LicenseUrl', '')}), via Wikimedia Commons: {url}. "
            "Cropped, darkened and overlaid with text.\n"
            "- Other covers use images from The Movie Database (TMDB). This product uses the TMDB API but is not "
            "endorsed or certified by TMDB.\n")
    print("favourites art ok")


if __name__ == "__main__":
    main("--redraw" in sys.argv)
