import os, urllib.request
OUT = "refs/bondsel2"; os.makedirs(OUT, exist_ok=True)
for name, p in {"brosnan": "/jrnAZYfVTD0BSnEJoU7uDaGhzy6.jpg", "brosnan_b": "/q0kobcM0hda7r6BH4cWMCxa6EnC.jpg",
                "brosnan_gb": "/zODdoZo9dOXcnsK3sdgyy1zxd7Q.jpg", "dalton": "/qKzMU1liuwufWSHxBg6hdNzzQzx.jpg",
                "dalton_b": "/arOvMbyNkvBcRDSdvzQRgdtc5KK.jpg", "dalton_gb": "/9IA9XVccTZZOJ35WixVH6epmS9k.jpg"}.items():
    open(os.path.join(OUT, name + ".jpg"), "wb").write(urllib.request.urlopen("https://image.tmdb.org/t/p/original" + p, timeout=90).read())
print("ok")
