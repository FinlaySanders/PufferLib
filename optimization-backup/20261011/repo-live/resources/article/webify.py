#!/usr/bin/env python3
# Web versions: fit within 1600x900 without stretching or upscaling.
from PIL import Image; import glob, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")); os.makedirs("web", exist_ok=True)
for f in sorted(glob.glob("*.png")):
    im = Image.open(f).convert("RGB")
    im.thumbnail((1600, 900), Image.LANCZOS)
    im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(f"web/{f}", optimize=True)
    im.save(f"web/{f[:-4]}.jpg", quality=90, optimize=True, progressive=True)
    print(f"web/{f}: {os.path.getsize('web/'+f)//1024} KB png, {os.path.getsize('web/'+f[:-4]+'.jpg')//1024} KB jpg")
