import os, urllib.request
OUT = "refs/xmen_hi"; os.makedirs(OUT, exist_ok=True)
W = {'127585_20': '/6UoNcuwbgBk6Hb52FXw2OnDvifB.jpg', '127585_21': '/i8qpnuvh0uRPWPsgWzgyrxhD2p9.jpg', '127585_22': '/euOrb1KOPNI0NmZZFCOnenTjxtL.jpg', '127585_23': '/hEYwKNSl8v2f4Xwe3teTGwrZ4jN.jpg', '127585_24': '/t2c0fWPx1FYBLBdvktWEpH5onWG.jpg', '127585_25': '/wzI0expzsVGgYyYKPpbdkxbIYBs.jpg', '127585_26': '/kIzZBtqi9HZyfCinfhELQbCSyOb.jpg', '127585_34': '/bAvo7XwJ3y3kLCBkeVSdjFTKLID.jpg', '127585_35': '/lPct1XqiJepfdgXJYeGlQ2C3M2Z.jpg', '127585_36': '/lwUh8oW8gQfQwh8pt5nuesHpfPS.jpg', '36668_8': '/7klqeHzrukZTFVgB4xEOIzqKcZ3.jpg', '36668_38': '/gn4GWWjIoSsnVpRkvZZ7Vznwj1e.jpg', '293660_4': '/pcZT1Ouq99dY6J2iGXjMxw16x6o.jpg', '293660_30': '/nMKpconh6JTJ86eCQoGOH6ypDMN.jpg', '293660_35': '/99p0n6EhX6PebGIScQ0uRZ8aUv8.jpg', '36657_6': '/ypiv2HEiNftzrg9ovDCFv16Q6Ti.jpg'}
for k, p in W.items():
    open(f"{OUT}/{k}.jpg", "wb").write(urllib.request.urlopen("https://image.tmdb.org/t/p/original" + p, timeout=120).read())
print("ok", len(W))
