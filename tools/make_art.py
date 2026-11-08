"""
SCREAMER (NINE HANDS | DSP) - visuel du plugin, entierement synthetise : pedale simple.

Habillage original NINE HANDS | DSP (pas une copie du boitier Ibanez) : boitier alu peint rouge sang de boeuf
metallise, serigraphie creme (Poppins), trois potards en ligne DRIVE / TONE / LEVEL, nom SCREAMER au centre,
ecran d'etat + barre de presets dessines par le plugin, LED rouge, footswitch, logo NINE HANDS | DSP blanc en bas.
Pieces photo du kit NINE HANDS | DSP (potard, LED, footswitch, embases jack : tools/photo_controls.py, repris de Darkbass).
Une seule lumiere pour toute la pedale : en haut a gauche (ombres portees vers le bas a droite).

Repere du plugin : 760 x 958 unites (format simple, comme Echoflex / Doorn / Strong Pickle), images en 2x (1520 x 1916).
Sorties (racine du depot) :
  background.jpg   fond complet (boitier, serigraphie, potards fixes, footswitch, LED eteinte, jacks, logo)
  glow_red.png     facade eclairee par la LED rouge (canal alpha = seule la lumiere ajoutee)
  led_on.png       lentille allumee
  fs_refl.png      reflet rouge de la LED sur le flanc de l'ecrou du footswitch (calque alpha)
  Layout.h         reperes des commandes
  design/preview.png  apercu (LED allumee)
Usage : python3 tools/make_art.py
"""
import os, sys, math
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import photo_controls as PC

AS = 2                                   # pixels par unite (images 2x)
UW, UH = 760, 958
W, H = UW * AS, UH * AS

L = np.array([-0.46, -0.62, 0.64]); L /= np.linalg.norm(L)        # vers la lumiere (x droite, y bas, z vers l'oeil)
V = np.array([0.0, 0.0, 1.0]); HV = (L + V) / np.linalg.norm(L + V)

# ------------------------------------------------------------------ geometrie (unites)
PX0, PY0, PW, PH, PR = 150.0, 34.0, 460.0, 890.0, 30.0          # boitier (format 125B : 66 x 122 mm environ)
CX = PX0 + PW / 2
KNOB_Y, KNOB_R, KNOB_DX = 182.0, 47.0, 140.0
KNOBS = [(CX - KNOB_DX, KNOB_Y, 'DRIVE'), (CX, KNOB_Y, 'TONE'), (CX + KNOB_DX, KNOB_Y, 'LEVEL')]
TITLE_Y = 352.0
SUB_Y = 408.0
STATUS = (CX - 175.0, 452.0, 350.0, 56.0)       # ecran d'etat (dessine par le plugin)
PRESET = (CX - 175.0, 520.0, 350.0, 36.0)       # barre de presets (dessinee par le plugin)
LED = (CX, 668.0)
FS = (CX, 780.0)
LOGO_C = (CX, 893.0)
JACK_Y = PY0 + 0.36 * PH

# ------------------------------------------------------------------ outils
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
UX, UY = (XX + 0.5) / AS, (YY + 0.5) / AS

def rrect_sd(x, y, x0, y0, w, h, r):
    cx, cy = x0 + w / 2, y0 + h / 2
    qx = np.abs(x - cx) - (w / 2 - r); qy = np.abs(y - cy) - (h / 2 - r)
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r

def fbm(shape, scales, amps, seed=0):
    r = np.random.default_rng(seed); out = np.zeros(shape, np.float32)
    for s, a in zip(scales, amps):
        n = r.standard_normal((max(2, shape[0] // s + 2), max(2, shape[1] // s + 2))).astype(np.float32)
        out += a * cv2.resize(n, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
    return out

def over(dst, rgba, x0, y0):
    h, w = rgba.shape[:2]
    X0, Y0 = int(round(x0)), int(round(y0))
    sx0, sy0 = max(0, -X0), max(0, -Y0)
    ex, ey = min(w, W - X0), min(h, H - Y0)
    a = rgba[sy0:ey, sx0:ex, 3:4] / 255.0
    reg = dst[Y0 + sy0:Y0 + ey, X0 + sx0:X0 + ex]
    dst[Y0 + sy0:Y0 + ey, X0 + sx0:X0 + ex] = reg * (1 - a) + rgba[sy0:ey, sx0:ex, :3] * a

# ------------------------------------------------------------------ 1. surface autour de la pedale (sombre, legerement eclairee en haut a gauche)
img = np.zeros((H, W, 3), np.float32)
base = 12.0 + 9.0 * np.exp(-(((UX - 150) / 600) ** 2 + ((UY - 120) / 700) ** 2))
img[:] = (base + fbm((H, W), [3, 40], [1.0, 0.9], 1))[..., None] * np.array([1.0, 0.99, 0.98])

sd = rrect_sd(UX, UY, PX0, PY0, PW, PH, PR)
body = np.clip(0.5 - sd * AS, 0, 1)
sh_m = cv2.GaussianBlur((rrect_sd(UX - 14, UY - 20, PX0, PY0, PW, PH, PR) < 0).astype(np.float32), (0, 0), 20 * AS)
ct_m = cv2.GaussianBlur((rrect_sd(UX - 3, UY - 4, PX0, PY0, PW, PH, PR) < 0).astype(np.float32), (0, 0), 4 * AS)
img *= (1 - 0.72 * sh_m - 0.35 * ct_m)[..., None]

# ------------------------------------------------------------------ 2. boitier : peinture rouge sang de boeuf metallisee, arete arrondie
EDGE = 9.0
d_in = np.clip(-sd, 0, None)
hgt = np.where(d_in < EDGE, np.sqrt(np.clip(EDGE ** 2 - (EDGE - d_in) ** 2, 0, None)), EDGE)
gy, gx = np.gradient(cv2.GaussianBlur(hgt, (0, 0), 1.0), 1.0 / AS)
nrm = np.dstack([-gx, -gy, np.ones_like(hgt)]); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
ndl = np.clip(nrm @ L, 0, 1); ndh = np.clip(nrm @ HV, 0, 1)
paint = np.array([92.0, 16.0, 20.0])                      # rouge sang de boeuf
encl = paint * (0.50 + 0.78 * ndl)[..., None] + (70 * ndh ** 40 + 18 * ndh ** 6)[..., None] * np.array([1.0, 0.82, 0.8])
# paillettes metalliques : points fins qui accrochent la lumiere, plus nombreux dans le reflet large
rng = np.random.default_rng(11)
flake = (rng.random((H, W)) ** 18).astype(np.float32)
flake = cv2.GaussianBlur(flake, (0, 0), 0.6) * 160
sheen = np.exp(-(((UX - 300) / 300) ** 2 + ((UY - 200) / 330) ** 2))
grain = fbm((H, W), [1, 2], [1.4, 0.8], 3) + 0.7 * fbm((H, W), [90, 260], [0.7, 0.9], 4)
encl += (grain[..., None] * np.array([1.0, 0.45, 0.45]))
encl += (flake * (0.35 + 0.9 * sheen))[..., None] * np.array([1.0, 0.55, 0.5])
encl += (24.0 * sheen)[..., None] * np.array([1.0, 0.42, 0.4])
img = img * (1 - body[..., None]) + encl * body[..., None]

# ------------------------------------------------------------------ 3. serigraphie creme (masques sur-echantillonnes 2x)
SS = 2
K = AS * SS
KW, KH = W * SS, H * SS
FONT_MED = os.path.join(ROOT, 'assets', 'fonts', 'Poppins-Medium.ttf')
FONT_BOLD = os.path.join(ROOT, 'assets', 'fonts', 'Poppins-Bold.ttf')
FONT_LIGHT = os.path.join(ROOT, 'assets', 'fonts', 'Poppins-Light.ttf')
ink_im = Image.new('L', (KW, KH), 0)
dr = ImageDraw.Draw(ink_im)

def spaced(x, y, txt, font, track, anchor='m', d=None):
    d = d or dr
    widths = [font.getlength(ch) for ch in txt]
    total = sum(widths) + track * K * (len(txt) - 1)
    cx = x * K - total / 2 if anchor == 'm' else (x * K if anchor == 'l' else x * K - total)
    for ch, w in zip(txt, widths):
        d.text((cx, y * K), ch, font=font, fill=255, anchor='lm')
        cx += w + track * K
    return total / K

f_lab = ImageFont.truetype(FONT_MED, int(22 * K))
f_io = ImageFont.truetype(FONT_MED, int(17 * K))
f_title = ImageFont.truetype(FONT_BOLD, int(54 * K))
f_sub = ImageFont.truetype(FONT_LIGHT, int(19 * K))
for (x, y, txt) in KNOBS:
    spaced(x, y - KNOB_R - 32, txt, f_lab, 3.5)
    for i in range(11):                                   # graduations 0 a 10 sur 300 degres
        a = math.radians(-150 + 30 * i)
        rr = KNOB_R + 11
        px, py = x + rr * math.sin(a), y - rr * math.cos(a)
        dd = 2.2 if i in (0, 5, 10) else 1.4
        dr.ellipse(((px - dd) * K, (py - dd) * K, (px + dd) * K, (py + dd) * K), fill=255)
# nom et sous-titre
tw = spaced(CX, TITLE_Y, 'SCREAMER', f_title, 4.0)
spaced(CX, SUB_Y, 'OVERDRIVE', f_sub, 9.0)
# filets de part et d'autre du sous-titre
sw = f_sub.getlength('OVERDRIVE') / K + 9.0 * 8
for sgn in (-1, 1):
    x0 = CX + sgn * (sw / 2 + 14); x1 = CX + sgn * (tw / 2 - 6)
    dr.rectangle((min(x0, x1) * K, (SUB_Y - 0.9) * K, max(x0, x1) * K, (SUB_Y + 0.9) * K), fill=255)
# IN / OUT tournes de 90 degres le long des tranches, a la hauteur des jacks
def spaced_rot(cx, cy, txt, font, track):
    widths = [font.getlength(ch) for ch in txt]
    total = sum(widths) + track * K * (len(txt) - 1)
    hpx = int(font.size * 1.6)
    t = Image.new('L', (int(total) + 8, hpx), 0); td = ImageDraw.Draw(t)
    x = 4
    for ch, w in zip(txt, widths):
        td.text((x, hpx / 2), ch, font=font, fill=255, anchor='lm'); x += w + track * K
    t = t.rotate(90, expand=True)
    ink_im.paste(255, (int(cx * K - t.width / 2), int(cy * K - t.height / 2)), t)
spaced_rot(PX0 + 26, JACK_Y, 'OUT', f_io, 2.0)
spaced_rot(PX0 + PW - 26, JACK_Y, 'IN', f_io, 2.0)

ink = cv2.resize(np.asarray(ink_im, np.float32) / 255.0, (W, H), interpolation=cv2.INTER_AREA)
wear = cv2.GaussianBlur((fbm((H, W), [1, 3], [1.0, 0.6], 21) > 2.5).astype(np.float32), (0, 0), 0.5)
ink = ink * (1 - wear * 0.45) * body
light = 1.0 + 0.05 * np.clip(1 - (UX - PX0) / PW * 0.6 - (UY - PY0) / PH * 0.6, -1, 1)
ink_col = np.array([236.0, 226.0, 204.0]) * light[..., None]          # creme
img = img * (1 - ink[..., None]) + ink_col * ink[..., None]

# ------------------------------------------------------------------ 4. logo NINE HANDS | DSP (blanc), en bas au centre
logo = np.asarray(Image.open(os.path.join(ROOT, 'assets', 'nine_hands_logo_blanc.png')).convert('RGBA')).astype(np.float32)
LOGO_W = 196.0
lw, lh = int(LOGO_W * AS), int(round(LOGO_W * AS * logo.shape[0] / logo.shape[1]))
lrgb = cv2.resize(logo[..., :3], (lw, lh), interpolation=cv2.INTER_AREA)
la = cv2.resize(logo[..., 3], (lw, lh), interpolation=cv2.INTER_AREA) / 255.0
lx0, ly0 = int(LOGO_C[0] * AS - lw / 2), int(LOGO_C[1] * AS - lh / 2)
reg = img[ly0:ly0 + lh, lx0:lx0 + lw]
lcol = lrgb * 0.92 * light[ly0:ly0 + lh, lx0:lx0 + lw, None]
img[ly0:ly0 + lh, lx0:lx0 + lw] = reg * (1 - la[..., None]) + lcol * la[..., None]
img += (fbm((H, W), [1], [0.9], 22) * body)[..., None]          # le grain de la peinture reste visible

# ------------------------------------------------------------------ 5. potards (photo du kit, repere efface : seul le repere du plugin tourne)
print('potards, LED, footswitch...')
KN, KS = PC.knob_sprite(KNOB_R, AS)
for (x, y, _) in KNOBS:
    over(img, KN, (x - KS / 2) * AS, (y - KS / 2) * AS)

# LED rouge (photo du kit, couleur d'origine)
LED_LENS = 12.0
LD, LDON, LS = PC.led_sprites(LED_LENS, AS, colour='red')
over(img, LD, (LED[0] - LS / 2) * AS, (LED[1] - LS / 2) * AS)
Image.fromarray(np.clip(LDON, 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(ROOT, 'led_on.png'))
LED_RING = LED_LENS * 1.07

# footswitch (photo du kit : ecrou hexagonal + bouton en metal tourne, reference Echoflex)
FS_FLATS = 100.0
FSPR, FSREFL, FS_W, FS_BTN = PC.footswitch_sprite(FS_FLATS, AS, refl_colour=(255.0, 70.0, 50.0))
over(img, FSPR, (FS[0] - FS_W / 2) * AS, (FS[1] - FS_W / 2) * AS)
Image.fromarray(FSREFL, 'RGBA').save(os.path.join(ROOT, 'fs_refl.png'))

# ------------------------------------------------------------------ 6. embases jack (photo du kit) : OUT a gauche, IN a droite
JACK_LEN = 104.0
for side in (-1, 1):
    j, jw_u, jh_u = PC.jack_sprite(JACK_LEN, AS, side)
    jh, jw = j.shape[:2]
    x0 = (PX0 * AS - jw + 2) if side < 0 else ((PX0 + PW) * AS - 2)
    y0 = JACK_Y * AS - jh / 2
    sh = np.zeros((H, W), np.float32)
    sh[int(y0):int(y0) + jh, int(x0):int(x0) + jw] = j[..., 3] / 255.0
    sh = (cv2.GaussianBlur(cv2.warpAffine(sh, np.float32([[1, 0, 10], [0, 1, 14]]), (W, H)), (0, 0), 8) * 0.6
          + cv2.GaussianBlur(cv2.warpAffine(sh, np.float32([[1, 0, 2], [0, 1, 3]]), (W, H)), (0, 0), 2) * 0.35) * (1 - body)
    img *= (1 - np.clip(sh, 0, 0.8))[..., None]
    over(img, j, x0, y0)

# ------------------------------------------------------------------ 7. sauvegarde du fond
bg8 = np.clip(img, 0, 255).astype(np.uint8)
Image.fromarray(bg8).save(os.path.join(ROOT, 'background.jpg'), quality=94, subsampling=0)

# ------------------------------------------------------------------ 8. facade eclairee par la LED rouge (calque alpha : seule la lumiere ajoutee)
GR = 110.0
def glow(c, fn):
    x0p, y0p = round((c[0] - GR) * AS), round((c[1] - GR) * AS)
    size = round(2 * GR * AS)
    reg = img[y0p:y0p + size, x0p:x0p + size].astype(np.float64)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    d = np.hypot((xx + 0.5) / AS - GR, (yy + 0.5) / AS - GR)
    h1, h2 = 8.0, 30.0                                      # petite source au-dessus de la facade : tache serree + diffusion large
    E = 1.1 * h1 ** 3 / (d ** 2 + h1 ** 2) ** 1.5 + 0.176 * h2 ** 3 / (d ** 2 + h2 ** 2) ** 1.5
    E *= np.clip((GR - d) / 30.0, 0, 1)
    E[d < LED_RING] *= 0.0
    col = np.array([1.0, 0.20, 0.12])
    lum = reg.mean(2, keepdims=True)
    lit = reg + (reg * 2.2 + 12.0 * np.clip(lum / 40.0, 0.3, 1.6)) * E[..., None] * col
    add = lit - reg
    a = np.clip(np.abs(add).max(-1) / 12.0, 0, 1)
    rgb = np.where(a[..., None] > 1e-3, reg + add / np.maximum(a, 1e-3)[..., None], reg)
    Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8), 'RGBA').save(os.path.join(ROOT, fn))
    return (x0p / AS, y0p / AS, size / AS, size / AS)
GLR = glow(LED, 'glow_red.png')

# ------------------------------------------------------------------ 9. Layout.h
def f(v): return f"{v:.2f}f"
def PT(p): return "{ %s, %s }" % (f(p[0]), f(p[1]))
def RC(r): return "{ %s, %s, %s, %s }" % (f(r[0]), f(r[1]), f(r[2]), f(r[3]))
with open(os.path.join(ROOT, 'Layout.h'), 'w') as fo:
    fo.write(f"// genere par tools/make_art.py - ne pas modifier a la main (repere {UW} x {UH}, fond 2x)\n#pragma once\n#include <juce_graphics/juce_graphics.h>\nnamespace layout\n{{\n")
    fo.write("    // ordre : drive, tone, level\n")
    fo.write("    const juce::Point<float> knobPos[3] = { " + ", ".join(PT(k[:2]) for k in KNOBS) + " };\n")
    fo.write(f"    const float knobR = {f(KNOB_R)};\n")
    fo.write(f"    const juce::Point<float> ledPos {PT(LED)}; const float ledS = {f(LS)};\n")
    fo.write(f"    const juce::Rectangle<float> glowRect {RC(GLR)};\n")
    fo.write(f"    const juce::Point<float> fsPos {PT(FS)}; const float footR = {f(FS_BTN)}, fsS = {f(FS_W)};   // bouton / sprite\n")
    fo.write(f"    const juce::Rectangle<float> statusRect {RC(STATUS)}, presetRect {RC(PRESET)};\n")
    fo.write(f"    const float statusFont = {f(28.0)}, presetFont = {f(21.0)};\n")
    fo.write(f"    const juce::Rectangle<float> boxRect {RC((PX0, PY0, PW, PH))};   // boitier (notice)\n")
    fo.write(f"    const float jackY = {f(JACK_Y)};\n")
    fo.write("}\n")

# ------------------------------------------------------------------ 10. apercu (LED allumee, ecran et barre esquisses)
prev = img.copy()
gi = np.asarray(Image.open(os.path.join(ROOT, 'glow_red.png'))).astype(np.float32)
over(prev, gi, GLR[0] * AS, GLR[1] * AS)
over(prev, LDON, (LED[0] - LS / 2) * AS, (LED[1] - LS / 2) * AS)
over(prev, FSREFL.astype(np.float32), (FS[0] - FS_W / 2) * AS, (FS[1] - FS_W / 2) * AS)
os.makedirs(os.path.join(ROOT, 'design'), exist_ok=True)
Image.fromarray(np.clip(prev, 0, 255).astype(np.uint8)).resize((UW, UH), Image.LANCZOS).save(os.path.join(ROOT, 'design', 'preview_art.png'))
print('ok')
