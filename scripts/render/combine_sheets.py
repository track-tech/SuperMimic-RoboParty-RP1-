"""Stack the G1 and RP1 contact sheets into one labelled comparison image."""

from PIL import Image, ImageDraw, ImageFont

g1 = Image.open(r"F:\Personal Project\deepseek-harness_ws\supermimic\g1_walk.png")
rp1 = Image.open(r"F:\Personal Project\deepseek-harness_ws\supermimic\rp1_walk.png")

w = min(g1.width, rp1.width)
band = 30
out = Image.new("RGB", (w, g1.height + rp1.height + 2 * band + 8), (16, 16, 16))
out.paste(g1.crop((0, 0, w, g1.height)), (0, band))
out.paste(rp1.crop((0, 0, w, rp1.height)), (0, band + g1.height + 8 + band))

draw = ImageDraw.Draw(out)
try:
    font = ImageFont.truetype("arial.ttf", 19)
except OSError:
    font = ImageFont.load_default()

draw.text((8, 6), "G1  ckpt_006000", fill=(235, 235, 235), font=font)
draw.text((250, 6), "walk1_subject1   solid = SuperMimic policy, blue = reference ghost",
          fill=(150, 180, 240), font=font)
draw.text((8, band + g1.height + 14), "RP1  ckpt_012000", fill=(235, 235, 235), font=font)

dst = r"F:\Personal Project\deepseek-harness_ws\supermimic\g1_vs_rp1_walk.png"
out.save(dst, optimize=True)
print("wrote", dst, out.size)
