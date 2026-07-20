"""Extract the ROBOT (no speech bubbles / music notes) from the logo
public/images/robot.svg into public/images/robot-mascot.svg, with the mouth
split into its own path so page CSS can animate it (#lessonMascot.talk .mMouthR).

The logo is one compound path of 52 subpaths (nonzero winding: white face/eye
interiors are counter-wound holes IN the same path — so robot subpaths must
stay together in one path; we only REMOVE whole bubble features and RELOCATE
the mouth pair). Subpath classification (index -> feature) was derived by
bounding box (see scratchpad svg_subpaths.py output, session 2026-07-17):
  bubbles + notes + tails/dots: x-range <= 220 or >= 490, AND y-end <= 297
  (the arms also live at the x extremes but start below y 350, so the y cut
   separates them safely)
  mouth: subpaths 16 (outer lips) + 35 (inner hole) around (317..396, 216..255)
Run:  python tools/build_robot_mascot.py
"""
import os
import re
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "public", "images", "robot.svg")
OUT = os.path.join(ROOT, "public", "images", "robot-mascot.svg")

ns = {"s": "http://www.w3.org/2000/svg"}
root = ET.parse(SRC).getroot()
d = root.findall(".//s:path", ns)[0].get("d")
subs = re.findall(r"M[^M]+", d)
assert len(subs) == 52, f"robot.svg changed: expected 52 subpaths, got {len(subs)}"


def bbox(s):
    nums = [float(x) for x in re.findall(r"-?\d+\.?\d*", s)]
    xs, ys = nums[0::2], nums[1::2]
    return min(xs), min(ys), max(xs), max(ys)


MOUTH_IDX = {16, 35}
body, mouth, dropped = [], [], []
for i, s in enumerate(subs):
    x0, y0, x1, y1 = bbox(s)
    if i in MOUTH_IDX:
        mouth.append(s)
    elif (x1 <= 220 or x0 >= 490) and y1 <= 297:
        dropped.append(i)  # speech bubbles, their notes, tails and dot trails
    else:
        body.append(s)

assert len(mouth) == 2 and len(dropped) == 12, (len(mouth), sorted(dropped))

svg = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="85 0 540 585">'
    '<path class="mBodyR" fill="rgb(11,11,11)" d="' + " ".join(body).strip() + '"/>'
    '<path class="mMouthR" fill="rgb(11,11,11)" d="' + " ".join(mouth).strip() + '"/>'
    "</svg>"
)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
print(f"wrote {OUT} ({os.path.getsize(OUT)/1024:.1f} KB; dropped subpaths {sorted(dropped)})")
