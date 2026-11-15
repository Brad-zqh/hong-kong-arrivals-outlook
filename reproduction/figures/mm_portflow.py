"""Render the MM-PortFlow architecture and its illustrative media inputs."""
import argparse
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Polygon, Circle, Arc
import numpy as np
from PIL import Image


here = Path(__file__).resolve().parent
assets = here.parents[1] / "site" / "assets"
cli = argparse.ArgumentParser(description=__doc__)
cli.add_argument("--out", type=Path, required=True, help="Directory for the paper and editable exports")
cli.add_argument("--site", action="store_true", help="Also update the website's portable SVG and WebP")
args = cli.parse_args()
args.out.mkdir(parents=True, exist_ok=True)
fig = plt.figure(figsize=(14.4, 9.645), dpi=200)
ax = fig.add_axes((0, 0, 1, 1), xlim=(0, 1440), ylim=(964.5, 0))
ax.set_axis_off()
plt.rcParams.update({"font.family": ["Times New Roman", "Liberation Serif"], "mathtext.fontset": "stix",
                     "pdf.fonttype": 42, "svg.fonttype": "none"})
ink = "#152550"
gold, rose, jade, blue, purple = "#e9ad40", "#d96d99", "#309f87", "#5a91dc", "#9074d1"


def tint(colour, proportion):
    rgb = np.array(to_rgb(colour))
    return 1 - proportion * (1 - rgb)


def rounded(x, y, w, h, colour, alpha=.10, rounded=6, dashed=False):
    edge = tint(colour, .55 if dashed else .78)
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={rounded}",
                               facecolor=tint(colour, alpha), edgecolor=edge, linewidth=.6,
                               linestyle=(0, (4, 2)) if dashed else "solid"))


def text(x, y, content, size=10, **kwargs):
    ax.text(x, y, content, fontsize=size, color=ink, va="center", **kwargs)


def arrow(x1, y1, x2, y2, colour=ink):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 linewidth=.9, color=colour, mutation_scale=8,
                                 shrinkA=0, shrinkB=0))


def line(*pairs, colour=ink):
    x, y = zip(*pairs)
    ax.plot(x, y, c=colour, lw=.85, solid_capstyle="round")


def block(x, y, w, h, label, colour, size=10):
    rounded(x, y, w, h, colour, .16)
    text(x+w/2, y+h/2, label, size, ha="center")


def tokens(x, y, count, colour, size=15):
    for i in range(count):
        a, b, d = x+i*(size+6), y, size*.34
        ax.add_patch(Polygon([(a,b),(a+d,b-d),(a+size+d,b-d),(a+size,b)],
                             fc=tint(colour,.23), ec=tint(colour,.66), lw=.40))
        ax.add_patch(Polygon([(a+size,b),(a+size+d,b-d),(a+size+d,b+size-d),(a+size,b+size)],
                             fc=tint(colour,.86), ec=colour, lw=.40))
        ax.add_patch(Rectangle((a,b),size,size,fc=tint(colour,.50),ec=tint(colour,.76),lw=.45))


def fit_image(img, x, y, w, h):
    height, width = img.shape[:2]
    ratio = w / h
    if width / height > ratio:
        margin = (width - int(height * ratio)) // 2
        img = img[:, margin:width-margin] if margin else img
    else:
        margin = (height - int(width / ratio)) // 2
        img = img[margin:height-margin] if margin else img
    ax.imshow(img, extent=(x,x+w,y+h,y), aspect="auto", interpolation="hanning", zorder=3)


rounded(10, 8, 1420, 145, blue, .065, dashed=True)
text(24, 28, "(a) Inputs and alignment", 18, weight="bold")
rounded(24, 53, 187, 83, gold, .10)
text(117, 66, "Arrivals · 56 days", 11, ha="center", weight="bold")
vals = [23,26,24,32,27,35,31,43,39,49,43,55,60,52,62,56,69,65]
xs, ys = np.linspace(37,196,len(vals)), 132 - np.array(vals)*.78
ax.fill_between(xs, ys, 123, color=tint(gold, .25))
ax.plot(xs, ys, c=gold, lw=1.1)
arrow(211, 92, 226, 92)
block(227, 77, 82, 31, "Log + center", blue)
line((309,92),(331,92),(331,53))
line((331,92),(331,131))
for y, title, tone in [(53,"History projection",gold),(92,"Daily Conv",rose),(131,"Weekly Conv",blue)]:
    arrow(331,y,349,y)
    block(350,y-12,126,24,title,tone)
    arrow(476,y,490,y)
    tokens(496,y-4,3,tone,11)
line((548,53),(825,53),(825,86))
for y, label, tone in [(92,"GELU · pool₇",rose),(131,"GELU · pool₂₈",blue)]:
    arrow(552,y,566,y)
    block(567,y-12,101,24,label,tone)
line((668,92),(689,92),(689,131),(668,131))
arrow(689,111.5,703,111.5)
block(704,99,96,25,"Concat → linear",jade,9)
line((800,112),(825,112),(825,86))
arrow(825,86,933,86)
for y, title, tone in [(53,"HK + mainland calendar",jade),(127,"Group · scope · lead",purple)]:
    block(885,y-12,145,24,title,tone,9.4)
arrow(951,65,951,72)
arrow(951,115,951,101)
block(934,73,35,27,"Σ",rose,15)
arrow(969,86,1001,86)
block(1002,73,85,27,"GELU",jade)
arrow(1087,86,1116,86)
rounded(1117, 49, 297, 78, gold, .11)
text(1132, 66, "History state H", 13, weight="bold")
tokens(1141,83,5,gold,16)
tokens(1141,107,5,gold,16)
text(1268, 92, "Citywide + checkpoint", 10)

rounded(10, 163, 1420, 251, blue, .065, dashed=True)
for x, w, name, tone in [(23,543,"Six platforms and media samples",blue),
                         (577,354,"Embeddings and scene cues",jade),
                         (942,475,"Time and place alignment",purple)]:
    rounded(x, 173, w, 230, tone, .06, dashed=True)
    text(x+12, 192, name, 14, weight="bold")

platform_logos = np.asarray(Image.open(here / "platform-icons.webp").convert("RGB"))
ax.imshow(platform_logos, extent=(36,174,332,250), aspect="auto", interpolation="hanning", zorder=3)
line((174,291),(193,291),(193,241))
line((193,291),(193,359))
for yy in (241,300,359):
    arrow(193,yy,212,yy)

rounded(213,218,209,47,rose,.11)
text(224,230,"Text",9,weight="bold")
text(224,250,"“Saturday train to West Kowloon”",10)
rounded(213,277,209,47,jade,.11)
text(224,300,"Photo",10,weight="bold")
fit_image(np.asarray(Image.open(assets/"west-kowloon.webp").convert("RGB")), 275,280,143,41)
rounded(213,336,209,47,blue,.11)
text(224,359,"Video",10,weight="bold")
ax.add_patch(Rectangle((275,340),143,39,fc=ink,ec="none"))
video = cv2.VideoCapture(str(assets/"star-ferry.mp4"))
for idx, frac in enumerate((.13,.47,.81)):
    video.set(cv2.CAP_PROP_POS_FRAMES, int(frac * video.get(cv2.CAP_PROP_FRAME_COUNT)))
    ok, frame = video.read()
    if not ok:
        raise RuntimeError("Could not read a frame from the licensed ferry clip")
    fit_image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), 278+46*idx,345,44,29)
video.release()
for x in range(279,415,8):
    for y in (342,375):
        ax.add_patch(Rectangle((x,y),4,2,fc="white",ec="none"))

for y, name, tone in [(241,"Qwen3",rose),(300,"CLIP",jade),(359,"CLIP",blue)]:
    arrow(422,y,448,y)
    block(449,y-14,83,28,name,tone,11)
    arrow(532,y,596,y)
    tokens(602,y-6,4,tone,13)
    arrow(682,y,706,y)

for y, label, tone in [(241,"Text embedding",rose),(300,"Photo + scene",jade)]:
    block(707,y-15,131,30,label,tone)
    arrow(838,y,860,y)
rounded(707,333,134,54,blue,.11)
for i, (label, sequence) in enumerate(zip(("Mean","Peak − μ","Persist.","Δ"),
        ([4,6,7,6,5],[3,3,8,4,3],[3,6,6,6,3],[3,4,5,7,8]))):
    x = 716+i*32
    ax.plot(np.linspace(x,x+21,5), 368-np.array(sequence)*2, c=blue, lw=1)
    text(x+10,378,label,6.6,ha="center")
arrow(841,359,860,359)
line((860,241),(860,359))
arrow(860,300,880,300)
for i, tone in enumerate((rose,jade,blue)):
    tokens(886,280+i*20,2,tone,10)
arrow(920,300,963,300)
block(964,285,69,30,"Cutoff",blue)
arrow(1033,300,1047,300)
block(1048,285,69,30,"Place",jade)
ax.add_patch(Circle((998,251), 12, fc=tint(blue,.13), ec=blue, lw=.9))
line((998,243),(998,251),(1004,253),colour=blue)
arrow(998,265,998,283,blue)
ax.add_patch(Polygon([(1083,267),(1073,255),(1072,248),(1076,241),(1083,239),
                      (1090,241),(1094,248),(1093,255)], fc=tint(jade,.23), ec=jade, lw=.9))
ax.add_patch(Circle((1083,249), 3, fc="white", ec=jade, lw=.65))
arrow(1083,269,1083,283,jade)
arrow(1117,300,1139,300)
line((1139,258),(1139,342))
for y, label, tone in [(258,"Citywide",gold),(342,"Checkpoint",purple)]:
    arrow(1139,y,1170,y)
    rounded(1171,y-26,217,51,tone,.12)
    tokens(1186,y-5,4,tone,14)
    text(1274,y+2,label,11,weight="bold")
text(1278, 382, "Platform · modality · age", 10, ha="center")


def matrix(x, y, values, colour, cell=14):
    for row, series in enumerate(values):
        for col, value in enumerate(series):
            ax.add_patch(Rectangle((x + col*cell, y + row*cell), cell, cell,
                                   fc=tint(colour, .08 + .80*value), ec="white", lw=.55))


def operation(x, y, symbol, colour):
    ax.add_patch(Circle((x, y), 11, fc=tint(colour, .16), ec=colour, lw=.75))
    text(x, y, symbol, 13, ha="center")


rounded(10, 426, 831, 411, blue, .065, dashed=True)
text(24, 446, "(b) Evidence attention", 18, weight="bold")
rounded(25, 468, 310, 67, gold, .075)
text(39, 485, "History state H", 12, weight="bold")
tokens(40, 501, 4, gold, 13)
arrow(114, 507, 133, 507)
block(134, 495, 55, 24, r"$W_Q$", rose, 12)
arrow(189, 507, 208, 507)
tokens(214, 501, 3, rose, 13)
text(279, 507, r"$Q$", 12)
line((335, 507), (350, 507), (350, 578))
arrow(350, 578, 381, 578)

rounded(25, 551, 181, 153, purple, .07)
text(39, 570, "Evidence cells", 12, weight="bold")
for i, (label, tone) in enumerate((("Platform", purple), ("Modality", blue), ("Age", jade), ("Count + plan rate", gold))):
    y = 596 + 28*i
    tokens(41, y-7, 2, tone, 12)
    text(85, y, label, 10)
line((206, 627), (220, 627), (220, 596))
line((220, 627), (220, 666))
for y, term, variable, tone in [(596, r"$W_K$", r"$K$", blue), (666, r"$W_V$", r"$V$", jade)]:
    arrow(220, y, 232, y)
    block(233, y-12, 52, 24, term, tone, 12)
    arrow(285, y, 298, y)
    tokens(303, y-6, 2, tone, 12)
    text(342, y, variable, 12)
arrow(355, 596, 381, 596)

block(370, 477, 117, 27, "Count prior", purple, 10.4)
block(370, 513, 117, 27, "Empty-cell mask", blue, 10.4)
line((487, 490), (497, 490), (497, 548), (435, 548))
arrow(429, 540, 429, 562)
arrow(445, 548, 445, 562)
rounded(382, 563, 92, 66, rose, .09)
text(428, 580, r"$QK^{\mathsf{T}}/\sqrt{d}$", 13, ha="center")
scores = [[.20, .70, .35, .29, .48], [.88, .38, .62, .18, .38], [.45, .71, .40, .74, .18]]
matrix(400, 593, scores, rose, cell=11)
block(493, 513, 106, 27, "Null option", blue, 10.4)
arrow(527, 540, 527, 581)
arrow(474, 596, 514, 596)
operation(527, 596, "+", blue)
arrow(538, 596, 555, 596)
block(556, 582, 82, 28, "Softmax", blue, 11)
arrow(638, 596, 652, 596)
rounded(653, 559, 163, 74, blue, .09)
text(734, 575, "Attention weights A", 11, ha="center", weight="bold")
matrix(701, 587, [row+[.58] for row in scores], blue, cell=11)

line((356, 666), (493, 666), (493, 691))
arrow(493, 691, 540, 691)
line((734, 633), (734, 651), (599, 651))
arrow(599, 651, 599, 674)
block(541, 675, 118, 32, "Weighted sum", jade, 11)
arrow(659, 691, 687, 691)
block(688, 675, 128, 32, "Gated residual", rose, 11)
arrow(752, 707, 752, 731)
line((48, 535), (48, 543), (18, 543), (18, 754), (529, 754))
text(485, 742, r"$H$", 11)
arrow(529, 754, 539, 754)
rounded(540, 732, 276, 47, purple, .11)
text(552, 755, r"$H^{\prime}=H+\mathrm{gated\ residual}$", 13)
tokens(735, 765, 3, purple, 13)
text(39, 808, "Applied separately at citywide and checkpoint scopes", 11)


rounded(853, 426, 577, 411, jade, .065, dashed=True)
text(868, 446, "(c) Directed checkpoint routing", 18, weight="bold")
rounded(868, 468, 547, 66, blue, .075)
text(880, 487, "Citywide state", 11, weight="bold")
tokens(881, 502, 4, gold, 13)
arrow(959, 508, 1011, 508)
block(1012, 494, 132, 28, "Demand head", blue, 11)
arrow(1144, 508, 1172, 508)
text(1180, 487, r"Group total $T$", 11, weight="bold")
tokens(1182, 502, 5, blue, 13)

rounded(868, 546, 547, 145, gold, .075)
text(880, 565, "Port states", 11, weight="bold")
for y, tone in [(584, rose), (603, blue), (622, jade)]:
    tokens(882, y, 4, tone, 12)
arrow(956, 609, 986, 609)
text(1049, 566, "Directed edge scores", 11, ha="center", weight="bold")
nodes = [(997, 610, blue), (1030, 587, rose), (1082, 609, jade), (1041, 632, gold)]
for left, right in [(0,1),(1,2),(0,3),(1,3),(3,2)]:
    x, y, _ = nodes[left]
    a, b, _ = nodes[right]
    direction = np.asarray((a-x, b-y), dtype=float)
    dx, dy = direction / np.linalg.norm(direction) * 8
    arrow(x+dx, y+dy, a-dx, b-dy)
for x, y, tone in nodes:
    ax.add_patch(Circle((x, y), 7, fc=tint(tone, .50), ec=tone, lw=.75, zorder=3))
text(1037, 661, "Distance + prior shares", 9.5, ha="center")
arrow(1037, 651, 1037, 641)
arrow(1090, 609, 1110, 609)
block(1111, 594, 92, 30, "Row softmax", blue, 9.5)
arrow(1203, 609, 1216, 609)
block(1217, 594, 76, 30, "Stay gate", purple, 9.5)
arrow(1293, 609, 1305, 609)
text(1353, 566, r"Transition $P$", 11, ha="center", weight="bold")
transition = [[.86,.22,.30,.13,.22],[.21,.86,.21,.36,.17],[.16,.20,.86,.13,.30],
              [.24,.16,.32,.86,.27],[.18,.27,.24,.16,.86]]
matrix(1325, 580, transition, gold, cell=11)
text(1352, 663, r"$p=p_0P$", 13, ha="center")

rounded(868, 703, 547, 119, purple, .085)
text(881, 722, "Forecast output", 12, weight="bold")
text(882, 752, r"Point forecast $T\,\times\,p$", 11)
text(882, 781, "History → interval size", 10.5)
tokens(882, 794, 4, blue, 11)
arrow(1022, 752, 1056, 752)
arrow(1032, 781, 1056, 781)
text(1223, 722, "15 days · 70% interval", 10.5, ha="center", weight="bold")
past_x = np.linspace(1073, 1202, 14)
past_y = [765, 770, 758, 769, 754, 763, 769, 751, 757, 745, 763, 753, 763, 756]
future_x = np.linspace(1202, 1399, 15)
future_y = np.array([756,759,766,750,755,749,753,761,758,760,748,751,748,744,745])
spread = np.linspace(4, 14, len(future_x))
ax.fill_between(future_x, future_y-spread, future_y+spread, color=tint(purple, .23))
line(*zip(past_x, past_y), colour=blue)
line(*zip(future_x, future_y), colour=purple)
line((1061, 791), (1402, 791), colour="#66789c")
ax.plot([1202, 1202], [738, 791], color="#66789c", lw=.65, ls="--")
for x, label in [(1092,"Past"),(1202,"Cutoff"),(1363,"Forecast")]:
    text(x, 805, label, 9, ha="center")


rounded(10, 849, 1420, 106, purple, .065, dashed=True)
text(24, 868, "Archived public feeds", 16, weight="bold")
for x, label, tone in [(24,"Nine-day weather outlook",gold),(260,"Checkpoint waiting times",blue),
                       (496,"Government press releases",purple),(732,"Special traffic news",jade)]:
    rounded(x, 884, 222, 55, tone, .095)
    text(x+50, 912, label, 10.5)

ax.add_patch(Circle((48, 910), 8, fc=tint(gold,.55), ec=gold, lw=.9))
for angle in np.linspace(0, 2*np.pi, 8, endpoint=False):
    dx, dy = np.cos(angle), np.sin(angle)
    line((48+11*dx, 910+11*dy), (48+14*dx, 910+14*dy), colour=gold)
ax.add_patch(Arc((281, 912), 24, 24, color=blue, lw=1.15))
line((281, 905), (281, 912), (287, 915), colour=blue)
ax.add_patch(Rectangle((508, 900), 19, 25, fc="white", ec=purple, lw=1.05))
for y in (907, 912, 917):
    line((512, y), (523, y), colour=purple)
ax.add_patch(Polygon([(740,925),(747,899),(759,899),(767,925)], fc=tint(jade,.34), ec=jade, lw=.9))
ax.plot([753, 753], [904, 921], color="white", lw=1.1, ls="--")
arrow(954, 912, 997, 912)
block(998, 895, 230, 34, "Timestamped archive", purple, 12)
arrow(1228, 912, 1259, 912)
tokens(1269, 905, 5, purple, 14)

stem = args.out / "mm-portflow-architecture"
fig.savefig(stem.with_suffix(".png"), dpi=200)
fig.savefig(stem.with_suffix(".svg"))
fig.savefig(stem.with_suffix(".pdf"))
if args.site:
    # Outline web fonts for identical rendering on devices without Times New Roman.
    web_figure = assets / "mm-portflow-architecture.svg"
    with matplotlib.rc_context({"svg.fonttype": "path", "svg.hashsalt": "mm-portflow"}):
        fig.savefig(web_figure, metadata={"Date": None})
    lines = web_figure.read_text(encoding="utf-8").splitlines()
    web_figure.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8", newline="\n")
    with Image.open(stem.with_suffix(".png")) as source:
        source.convert("RGB").save(assets / "mm-portflow-sunburst.webp", quality=95, method=6)
plt.close(fig)
