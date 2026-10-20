"""Favourites row art: key art + the show's logo (no vignette), hover GIFs, hero backdrops.

Everything is kept in this repo so nothing depends on Pinterest, Giphy or other hosts: the source images and GIFs
are mirrored once into spotlight/art/favourites/_sources/ and every output is built from those copies. Files are
only (re)built when missing, or with --redraw (which still uses the mirrored sources). Nothing here deletes files.

  Doctor Who  the user's cover (Pinterest) + gold Whoniverse logo; hover = the user's Whoniverse ident (Giphy)
  One Pace    One Piece crew art (TMDB) + One Pace logo (onepace.net); hover = One Piece logo opening (Funimation)
  Live Sport  night stadium (Wikimedia Commons, CC BY 3.0) + our broadcast logo; hover = floodlit stadium fireworks
  My Simkl    wall of trending posters (TMDB, frozen once) + our MY SIMKL logo; hover = the wall drifting
"""
import io, json, os, re, shutil, sys, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spotlight_art as art
from PIL import Image, ImageEnhance

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAV = os.path.join(ROOT, "spotlight", "art", "favourites")
SRC = os.path.join(FAV, "_sources")
LOGOS = os.path.join(ROOT, "spotlight", "logos")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36 nuvio-awards"}
COMMONS = "File:Germany and Argentina face off in the final of the World Cup 2014 -2014-07-13 (5).jpg"
SOURCES = {
    "doctorwho-art.jpg": "https://i.pinimg.com/1200x/ce/6d/19/ce6d198219d333e44c15ec35bd18e1f9.jpg",
    "doctorwho-hover.gif": "https://media.giphy.com/media/8dxHohVIpGxGPldCS9/giphy.gif",
    "onepace-art.jpg": "https://image.tmdb.org/t/p/original/6fRwRD7GdCfg6owzmCT3VgQtowl.jpg",
    "onepace-hover.gif": "https://media.giphy.com/media/D0jGorbyCnZyE/giphy.gif",
    "livesport-hover.gif": "https://media.giphy.com/media/cmMzVX4LV157ubMD6V/giphy.gif",
}
W, H = art.W, art.H


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()


def source(name):
    """Local mirror of a source file (downloaded once, then always read from the repo)."""
    path = os.path.join(SRC, name)
    if not os.path.exists(path):
        os.makedirs(SRC, exist_ok=True)
        data = commons_image() if name == "livesport-art.jpg" else fetch(SOURCES[name])
        open(path, "wb").write(data)
    return path


def commons_image():
    q = {"action": "query", "titles": COMMONS, "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": "1920",
         "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl", "format": "json"}
    d = json.loads(fetch("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(q)))
    ii = next(iter(d["query"]["pages"].values()))["imageinfo"][0]
    meta = {k: v.get("value", "") for k, v in ii.get("extmetadata", {}).items()}
    artist = re.sub(r"<[^>]+>", "", meta.get("Artist", "")).strip()
    open(os.path.join(ROOT, "spotlight", "art", "CREDITS.md"), "w", encoding="utf-8").write(
        "# Image credits\n\n"
        f"- **Live Sport** cover and backdrop: “{COMMONS[5:]}” by {artist}, {meta.get('LicenseShortName', '')} "
        f"({meta.get('LicenseUrl', '')}), via Wikimedia Commons: {ii['descriptionurl']}. Cropped, graded and overlaid "
        "with a logo.\n"
        "- Doctor Who, One Pace and Live Sport hover GIFs and the Doctor Who cover art were chosen by the user "
        "(Giphy / Pinterest) and are mirrored in `favourites/_sources/` so they cannot disappear.\n"
        "- Whoniverse logo: Wikimedia Commons (File:Whoniverse.svg); One Pace logo: onepace.net; Simkl glyph: "
        "Simple Icons (CC0).\n"
        "- Other covers use images from The Movie Database (TMDB). This product uses the TMDB API but is not "
        "endorsed or certified by TMDB.\n")
    return fetch(ii["thumburl"])


def save_jpg(im, *path, q=88):
    p = os.path.join(FAV, *path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    im.save(p, "JPEG", quality=q, optimize=True, progressive=True)


def want(*path, redraw=False):
    return redraw or not os.path.exists(os.path.join(FAV, *path))


def copy_hover(name, folder):
    dst = os.path.join(FAV, folder, "hover.gif")
    if not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(source(name), dst)


def logo(name):
    return Image.open(os.path.join(LOGOS, name))


def simkl_wall(size=(W, H), shift=0.0):
    """Tilted wall of posters in natural colour; shift (0..1) slides it along the tilt for the hover."""
    wall_path = os.path.join(SRC, "mysimkl-wall.png")
    if not os.path.exists(wall_path):
        from spotlight import tmdb
        posters = []
        for p in ("/trending/movie/week", "/trending/tv/week"):
            posters += [r["poster_path"] for r in (tmdb(p) or {}).get("results", []) if r.get("poster_path")]
        pw, ph, gap, cols, rows = 170, 255, 16, 12, 7
        wall = Image.new("RGB", (cols * (pw + gap), rows * (ph + gap)), (12, 12, 16))
        imgs = [im for im in (art.fetch(p, "w342") for p in posters[:40]) if im]
        for i in range(cols * (rows + 1)):
            im = imgs[i % len(imgs)].convert("RGB").resize((pw, ph), Image.LANCZOS)
            c, r = i % cols, i // cols
            wall.paste(im, (c * (pw + gap), r * (ph + gap) - (ph // 2 if c % 2 else 0)))
        os.makedirs(SRC, exist_ok=True)
        wall.save(wall_path)
    wall = Image.open(wall_path).convert("RGB").rotate(-12, resample=Image.BICUBIC, fillcolor=(12, 12, 16))
    x = (wall.width - W) // 2
    y = (wall.height - H) // 2 - round(120 * shift)
    crop = wall.crop((x, y, x + W, y + H))
    return ImageEnhance.Brightness(crop).enhance(0.82).resize(size, Image.LANCZOS)


def main(redraw=False):
    # Doctor Who
    if want("doctorwho", "cover.jpg", redraw=redraw):
        im = art.graded(Image.open(source("doctorwho-art.jpg")))
        save_jpg(art.put_logo(art.soft_fade(im), logo("whoniverse-gold.png"), maxw=600, maxh=190), "doctorwho", "cover.jpg")
        save_jpg(art.graded(Image.open(source("doctorwho-art.jpg")), 1, 1, (1920, 1080)), "doctorwho", "backdrop.jpg", q=84)
    copy_hover("doctorwho-hover.gif", "doctorwho")
    # One Pace
    if want("onepace", "cover.jpg", redraw=redraw) or want("onepace", "backdrop.jpg"):
        im = art.graded(Image.open(source("onepace-art.jpg")), 0.95)
        save_jpg(art.put_logo(art.soft_fade(im, 0.45, 190), logo("onepace.png"), maxw=520, maxh=200), "onepace", "cover.jpg")
        save_jpg(art.graded(Image.open(source("onepace-art.jpg")), 1, 1, (1920, 1080)), "onepace", "backdrop.jpg", q=84)
    copy_hover("onepace-hover.gif", "onepace")
    # Live Sport
    if want("livesport", "cover.jpg", redraw=redraw) or not os.path.exists(os.path.join(SRC, "livesport-art.jpg")):
        photo = Image.open(source("livesport-art.jpg"))
        im = art.graded(photo, 1.0, 1.08)
        save_jpg(art.put_logo(art.soft_fade(im, 0.5, 180), logo("livesport-a.png"), maxw=620, maxh=150), "livesport", "cover.jpg")
        save_jpg(art.graded(photo, 1, 1, (1920, 1080)), "livesport", "backdrop.jpg", q=84)
    copy_hover("livesport-hover.gif", "livesport")
    # My Simkl
    lg = logo("mysimkl-e.png")
    if want("mysimkl", "cover.jpg", redraw=redraw):
        save_jpg(art.put_logo(art.soft_fade(simkl_wall(), 0.4, 200), lg, maxw=560, maxh=150), "mysimkl", "cover.jpg")
    if want("mysimkl", "hover.gif", redraw=redraw):
        art.ken_burns_gif(os.path.join(FAV, "mysimkl", "hover.gif"),
                          lambda t: art.put_logo(art.soft_fade(simkl_wall(shift=t), 0.4, 200), lg, maxw=560, maxh=150),
                          frames=30, ms=90)
    print("favourites art ok")


if __name__ == "__main__":
    main("--redraw" in sys.argv)
