"""
SCREAMER (NINE HANDS | DSP) - visuel du plugin, entierement synthetise : pedale simple.

Habillage original NINE HANDS | DSP (pas une copie du boitier Ibanez) : boitier alu peint rouge sang de boeuf
metallise, serigraphie creme (Poppins), trois potards en ligne DRIVE / TONE / LEVEL, nom SCREAMER au centre,
ecran d'etat + barre de presets dessines par le plugin, LED rouge, footswitch, logo NINE HANDS | DSP blanc en bas.
Pieces photo du kit NINE HANDS | DSP (potard, LED, footswitch, embases jack : tools/photo_controls.py, repris de Darkbass).
Une seule lumiere pour toute la pedale : en haut a gauche (ombres portees vers le bas a droite).

Regle NINE HANDS | DSP des pedales simples : image du plugin de 965 x 1800 pixels, la pedale plein cadre (le boitier touche
le haut et le bas de l'image, les jacks touchent les bords gauche et droit), fond transparent seulement autour des jacks
(et dans les coins arrondis). Le dessin se fait dans un repere de travail 760 x 958 unites (2 px par unite), puis l'image
finale est recadree sur le boitier + jacks et mise a l'echelle : repere du plugin 482,5 x 900 unites = 965 x 1800 px / 2.
Sorties (racine du depot) :
  background.png   fond complet 965 x 1800 RGBA (boitier, serigraphie, potards fixes, footswitch, LED eteinte, jacks, logo)
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
OUT_W, OUT_H = 965, 1800                         # image finale (regle des pedales simples)
JACK_LEN = 104.0                                 # longueur de l'embase le long de la tranche
_jtest = PC.jack_sprite(JACK_LEN, AS, 1)
JACK_PROT = _jtest[1] - 1.5 / AS                 # saillie de l'embase hors du boitier (unites)
PY0, PH, PR = 34.0, 890.0, 30.0
PW = OUT_W / OUT_H * PH - 2 * JACK_PROT          # largeur du boitier : boitier + jacks = proportions de l'image finale
PX0 = (UW - PW) / 2
CX = PX0 + PW / 2
CROP_X0, CROP_W = PX0 - JACK_PROT, PW + 2 * JACK_PROT     # cadre final (unites de travail)
SC = (OUT_H / 2.0) / PH                          # unites de travail -> unites du plugin (965 x 1800 / 2)
# disposition des potards de la TS9 : DRIVE en haut a gauche, LEVEL en haut a droite, TONE plus petit au centre, plus bas
KNOB_R, TONE_R = 47.0, 37.0
KNOBS = [(CX - 118.0, 158.0, 'DRIVE', KNOB_R), (CX, 268.0, 'TONE', TONE_R), (CX + 118.0, 158.0, 'LEVEL', KNOB_R)]
TITLE_Y = 462.0                                   # titre au milieu de la pedale (bloc titre + sous-titre centre sur 479)
SUB_Y = 514.0
STATUS = (CX - 175.0, 552.0, 350.0, 56.0)       # ecran d'etat (dessine par le plugin)
PRESET = (CX - 175.0, 620.0, 350.0, 36.0)       # barre de presets (dessinee par le plugin)
LED = (CX, 708.0)
FS = (CX, 804.0)
LOGO_C = (CX, 896.0)
JACK_Y = PY0 + 0.62 * PH                         # jacks sous le milieu de la hauteur de la pedale

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
for (x, y, txt, KR) in KNOBS:
    spaced(x, y - KR - 32, txt, f_lab, 3.5)
    for i in range(11):                                   # graduations 0 a 10 sur 300 degres
        a = math.radians(-150 + 30 * i)
        rr = KR + 11
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

# ------------------------------------------------------------------ 3b. dessin du visage (design/source/portrait.svg), serigraphie creme
#     SCREAMER_PORTRAIT="cx,cy,largeur,opacite" (unites) : centre et largeur du dessin lui-meme (pas de son cadre SVG)
PORTRAIT = os.environ.get('SCREAMER_PORTRAIT', '')
if PORTRAIT:
    import subprocess, io
    pcx, pcy, pw_, pop = [float(v) for v in PORTRAIT.split(',')]
    BX0, BW_, BY0, BH_ = 0.156, 0.6625, 0.141, 0.72          # boite du dessin dans le cadre carre du SVG
    full = pw_ / BW_                                          # cote du cadre SVG (unites)
    npx = int(round(full * AS))
    png = subprocess.run(['rsvg-convert', '-w', str(npx), '-h', str(npx), os.path.join(ROOT, 'design', 'source', 'portrait.svg')],
                         capture_output=True, check=True).stdout
    pr = np.asarray(Image.open(io.BytesIO(png)).convert('RGBA')).astype(np.float32) / 255.0
    pm = pr[..., 3] * (1.0 - pr[..., :3].mean(-1))           # seuls les traits sombres deviennent de l'encre
    if os.environ.get('SCREAMER_FEATURES'):
        # seulement les yeux, le nez et la bouche (ellipses aux bords adoucis, coordonnees du cadre SVG / 800)
        vv, uu = np.mgrid[0:npx, 0:npx].astype(np.float32) * (800.0 / npx)
        keep = np.zeros_like(pm)
        for (ex_, ey_, rx_, ry_) in ((326.5, 381.5, 48.0, 26.0), (475.0, 381.5, 46.0, 26.0),      # yeux
                                     (402.5, 464.0, 50.0, 24.0),                                  # nez
                                     (402.5, 560.0, 66.0, 52.0)):                                 # bouche
            d_ = np.sqrt(((uu - ex_) / rx_) ** 2 + ((vv - ey_) / ry_) ** 2)
            keep = np.maximum(keep, np.clip((1.0 - d_) / 0.15, 0, 1))
        pm = pm * keep
    x0p = int(round((pcx - full * (BX0 + BW_ / 2)) * AS)); y0p = int(round((pcy - full * (BY0 + BH_ / 2)) * AS))
    lay = np.zeros((H, W), np.float32)
    sx0, sy0 = max(0, -x0p), max(0, -y0p); ex, ey = min(npx, W - x0p), min(npx, H - y0p)
    lay[y0p + sy0:y0p + ey, x0p + sx0:x0p + ex] = pm[sy0:ey, sx0:ex]
    ink = np.maximum(ink, lay * pop)
wear = cv2.GaussianBlur((fbm((H, W), [1, 3], [1.0, 0.6], 21) > 2.5).astype(np.float32), (0, 0), 0.5)
ink = ink * (1 - wear * 0.45) * body
light = 1.0 + 0.05 * np.clip(1 - (UX - PX0) / PW * 0.6 - (UY - PY0) / PH * 0.6, -1, 1)
ink_col = np.array([236.0, 226.0, 204.0]) * light[..., None]          # creme
# ------------------------------------------------------------------ 3c. grand visage imprime sur la coque (design/source/portrait.svg), encre noire
#     SCREAMER_ART="x,y,cote,opacite" (unites) : position de l'oeil droit du visage (oeil de gauche dans le dessin)
#     et cote du cadre carre du SVG. Le dessin reste sur le boitier (coupe a ses bords) et passe SOUS tous les elements :
#     serigraphie, logo, potards, LED, footswitch (reserves autour d'eux), ecran et barre dessines par le plugin.
ART = os.environ.get('SCREAMER_ART', '439,341,1980,0.95')    # v1.1.0 : visage valide (oeil sous TONE, bouche en bas a droite)
if ART:
    import subprocess, io
    ax_, ay_, full, aop = [float(v) for v in ART.split(',')]
    npx = int(round(full * AS))
    png = subprocess.run(['rsvg-convert', '-w', str(npx), '-h', str(npx), os.path.join(ROOT, 'design', 'source', 'portrait.svg')],
                         capture_output=True, check=True).stdout
    pr = np.asarray(Image.open(io.BytesIO(png)).convert('RGBA')).astype(np.float32) / 255.0
    pm = pr[..., 3] * (1.0 - pr[..., :3].mean(-1))           # seuls les traits sombres deviennent de l'encre
    x0p = int(round((ax_ - full * 326.5 / 800.0) * AS)); y0p = int(round((ay_ - full * 381.5 / 800.0) * AS))
    lay = np.zeros((H, W), np.float32)
    sx0, sy0 = max(0, -x0p), max(0, -y0p); ex, ey = min(npx, W - x0p), min(npx, H - y0p)
    if ex > sx0 and ey > sy0:
        lay[y0p + sy0:y0p + ey, x0p + sx0:x0p + ex] = pm[sy0:ey, sx0:ex]
    # reserves : serigraphie et logo (marge ~3 unites), potards, LED, footswitch
    keep_out = (ink > 0.05).astype(np.uint8)
    _lg = np.asarray(Image.open(os.path.join(ROOT, 'assets', 'nine_hands_logo_blanc.png')).convert('RGBA'))[..., 3]
    _lw = int(196.0 * AS); _lh = int(round(_lw * _lg.shape[0] / _lg.shape[1]))
    _la = cv2.resize(_lg, (_lw, _lh), interpolation=cv2.INTER_AREA) > 20
    _x0, _y0 = int(LOGO_C[0] * AS - _lw / 2), int(LOGO_C[1] * AS - _lh / 2)
    keep_out[_y0:_y0 + _lh, _x0:_x0 + _lw] |= _la.astype(np.uint8)
    keep_out = cv2.dilate(keep_out, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(6 * AS) | 1, int(6 * AS) | 1))).astype(np.float32)
    for (x, y, _, KR) in KNOBS:
        keep_out = np.maximum(keep_out, (np.hypot(UX - x, UY - y) < KR + 5).astype(np.float32))
    keep_out = np.maximum(keep_out, (np.hypot(UX - LED[0], UY - LED[1]) < 19).astype(np.float32))
    keep_out = np.maximum(keep_out, (np.hypot(UX - FS[0], UY - FS[1]) < 64).astype(np.float32))
    keep_out = cv2.GaussianBlur(keep_out, (0, 0), 1.2 * AS)
    # coupe au boitier, un peu en retrait de l'arete arrondie (le dessin est imprime sur le dessus)
    on_top = np.clip((-sd - 6.0) / 2.0, 0, 1)
    art_a = np.clip(lay * aop, 0, 1) * (1 - np.clip(keep_out * 1.6, 0, 1)) * on_top
    art_col = np.array([16.0, 8.0, 9.0]) + 10.0 * (light[..., None] - 1.0) * 10       # encre noire, a peine plus claire dans la lumiere
    img = img * (1 - art_a[..., None]) + art_col * art_a[..., None]
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
for (x, y, _, KR) in KNOBS:
    KN, KS = PC.knob_sprite(KR, AS)
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
#     hors du boitier le fond est transparent : pas d'ombre portee sur une surface, seul le metal de l'embase est opaque
alpha = body.copy()
for side in (-1, 1):
    j, jw_u, jh_u = PC.jack_sprite(JACK_LEN, AS, side)
    jh, jw = j.shape[:2]
    x0 = int(round((PX0 * AS - jw + 2) if side < 0 else ((PX0 + PW) * AS - 2)))
    y0 = int(round(JACK_Y * AS - jh / 2))
    over(img, j, x0, y0)
    ja = np.zeros((H, W), np.float32)
    ja[y0:y0 + jh, x0:x0 + jw] = j[..., 3] / 255.0
    alpha = np.maximum(alpha, ja)

# ------------------------------------------------------------------ 7. sauvegarde du fond : 965 x 1800, pedale plein cadre, transparent autour des jacks
def to_out(a):
    """recadre sur boitier + jacks (repere de travail) et met a l'echelle de l'image finale"""
    x0, x1 = CROP_X0 * AS, (CROP_X0 + CROP_W) * AS
    y0, y1 = PY0 * AS, (PY0 + PH) * AS
    M = np.float32([[OUT_W / (x1 - x0), 0, -x0 * OUT_W / (x1 - x0)], [0, OUT_H / (y1 - y0), -y0 * OUT_H / (y1 - y0)]])
    return cv2.warpAffine(a, M, (OUT_W, OUT_H), flags=cv2.INTER_AREA if OUT_H < (y1 - y0) else cv2.INTER_CUBIC)
out_rgb = np.clip(to_out(img), 0, 255); out_a = np.clip(to_out(alpha), 0, 1)
Image.fromarray(np.dstack([out_rgb, out_a * 255]).astype(np.uint8), 'RGBA').save(os.path.join(ROOT, 'background.png'), optimize=True)
if os.path.exists(os.path.join(ROOT, 'background.jpg')): os.remove(os.path.join(ROOT, 'background.jpg'))

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

# ------------------------------------------------------------------ 9. Layout.h (repere du plugin : 482,5 x 900 unites = image 965 x 1800 / 2)
def f(v): return f"{v:.2f}f"
def X(v): return (v - CROP_X0) * SC
def Y(v): return (v - PY0) * SC
def PT(p): return "{ %s, %s }" % (f(X(p[0])), f(Y(p[1])))
def RC(r): return "{ %s, %s, %s, %s }" % (f(X(r[0])), f(Y(r[1])), f(r[2] * SC), f(r[3] * SC))
import json
json.dump({"frame": [OUT_W / 2, OUT_H / 2], "knobs": [[X(k[0]), Y(k[1]), k[3] * SC] for k in KNOBS], "led": [X(LED[0]), Y(LED[1])],
           "fs": [X(FS[0]), Y(FS[1])], "status": [X(STATUS[0]), Y(STATUS[1]), STATUS[2] * SC, STATUS[3] * SC],
           "preset": [X(PRESET[0]), Y(PRESET[1]), PRESET[2] * SC, PRESET[3] * SC], "jackY": Y(JACK_Y),
           "jackL": X(PX0 - JACK_PROT / 2), "jackR": X(PX0 + PW + JACK_PROT / 2)},
          open(os.path.join(ROOT, 'tools', 'layout.json'), 'w'), indent=1)
with open(os.path.join(ROOT, 'Layout.h'), 'w') as fo:
    fo.write(f"// genere par tools/make_art.py - ne pas modifier a la main (repere {OUT_W / 2} x {OUT_H / 2} = fond {OUT_W} x {OUT_H} px / 2)\n#pragma once\n#include <juce_graphics/juce_graphics.h>\nnamespace layout\n{{\n")
    fo.write(f"    constexpr float frameW = {f(OUT_W / 2)}, frameH = {f(OUT_H / 2)};   // pedale plein cadre (jacks aux bords gauche / droit)\n")
    fo.write("    // ordre : drive, tone, level\n")
    fo.write("    const juce::Point<float> knobPos[3] = { " + ", ".join(PT(k[:2]) for k in KNOBS) + " };\n")
    fo.write("    const float knobR[3] = { " + ", ".join(f(k[3] * SC) for k in KNOBS) + " };\n")
    fo.write(f"    const juce::Point<float> ledPos {PT(LED)}; const float ledS = {f(LS * SC)};\n")
    fo.write(f"    const juce::Rectangle<float> glowRect {RC(GLR)};\n")
    fo.write(f"    const juce::Point<float> fsPos {PT(FS)}; const float footR = {f(FS_BTN * SC)}, fsS = {f(FS_W * SC)};   // bouton / sprite\n")
    fo.write(f"    const juce::Rectangle<float> statusRect {RC(STATUS)}, presetRect {RC(PRESET)};\n")
    fo.write(f"    const float statusFont = {f(28.0 * SC)}, presetFont = {f(21.0 * SC)};\n")
    fo.write(f"    const juce::Rectangle<float> boxRect {RC((PX0, PY0, PW, PH))};   // boitier\n")
    fo.write(f"    const float jackY = {f(Y(JACK_Y))};\n")
    fo.write("}\n")

# ------------------------------------------------------------------ 10. apercu (LED allumee, ecran et barre esquisses)
prev = img.copy()
gi = np.asarray(Image.open(os.path.join(ROOT, 'glow_red.png'))).astype(np.float32)
over(prev, gi, GLR[0] * AS, GLR[1] * AS)
over(prev, LDON, (LED[0] - LS / 2) * AS, (LED[1] - LS / 2) * AS)
over(prev, FSREFL.astype(np.float32), (FS[0] - FS_W / 2) * AS, (FS[1] - FS_W / 2) * AS)
os.makedirs(os.path.join(ROOT, 'design'), exist_ok=True)
pv = np.clip(to_out(prev), 0, 255); bgc = np.array([14.0, 14.0, 15.0])
pv = pv * out_a[..., None] + bgc * (1 - out_a[..., None])
Image.fromarray(pv.astype(np.uint8)).save(os.path.join(ROOT, 'design', 'preview_art.png'))
print('ok')
