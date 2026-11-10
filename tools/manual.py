# SCREAMER (NINE HANDS | DSP) - notice PDF en francais, illustree avec le rendu reel du plugin (couverture minimale commune).
# Usage : python3 tools/manual.py <dossier des captures (tools/render)> <fichier PDF de sortie>
import os, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, NextPageTemplate, Frame, Paragraph, Spacer, Image as RLImage,
                                Table, TableStyle, PageBreak, KeepTogether)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS, OUT = sys.argv[1], sys.argv[2]
VERSION = "1.3.5"
TMP = os.path.join(ROOT, "tools", "manual_assets"); os.makedirs(TMP, exist_ok=True)
FONTS = os.path.join(ROOT, "assets", "fonts")
for n, f in (("Pop", "Poppins-Regular"), ("PopL", "Poppins-Light"), ("PopM", "Poppins-Medium"), ("PopB", "Poppins-Bold"),
             ("Title", "BarlowCondensed-ExtraBold")):
    pdfmetrics.registerFont(TTFont(n, os.path.join(FONTS, f + ".ttf")))

ACC = colors.HexColor("#B3202A"); ACC_L = colors.HexColor("#FF6A55")        # rouge de la pedale / de la LED
DARK = colors.HexColor("#211617"); GREY = colors.HexColor("#6A5E5F"); LIGHT = colors.HexColor("#F6ECEA")

# reperes du plugin (repere = fond / 2, 900 unites de haut), ecrits par tools/make_art.py
import json
LAY = json.load(open(os.path.join(ROOT, "tools", "layout.json")))
KNOBS = [tuple(k[:2]) for k in LAY["knobs"]]          # drive, tone, level (disposition TS9)
LED, FS, JACK_Y = tuple(LAY["led"]), tuple(LAY["fs"]), LAY["jackY"]
STATUS, PRESET = tuple(LAY["status"]), tuple(LAY["preset"])

def shot(name): return Image.open(os.path.join(SHOTS, name)).convert("RGB")
src = shot("screamer_status.png")
k = src.height / LAY["frame"][1]

# ---------- capture annotee ----------
marks = [(1, KNOBS[0][0] - 62, KNOBS[0][1] - 58), (2, KNOBS[1][0] + 62, KNOBS[1][1] + 20), (3, KNOBS[2][0] + 62, KNOBS[2][1] - 58),
         (4, PRESET[0] + 4, PRESET[1] - 16), (5, LED[0] + 34, LED[1]),
         (6, FS[0] + 80, FS[1]), (7, LAY["jackL"] + 32, JACK_Y - 66), (8, LAY["jackR"] - 32, JACK_Y - 66)]
ann = src.copy(); dr = ImageDraw.Draw(ann)
fnt = ImageFont.truetype(os.path.join(FONTS, "Poppins-Bold.ttf"), 34)
for n, x, y in marks:
    cx, cy, r = x * k, y * k, 27
    dr.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255), outline=(179, 32, 42), width=5)
    dr.text((cx, cy + 1), str(n), font=fnt, fill=(33, 22, 23), anchor="mm")
annotated = os.path.join(TMP, "screamer_annotated.png"); ann.save(annotated)

def crop_u(im, box): return im.crop(tuple(int(v * k) for v in box))
def strip(parts, path, gap=18):
    s = Image.new("RGB", (sum(p.width for p in parts) + gap * (len(parts) - 1), max(p.height for p in parts)), (255, 255, 255))
    x = 0
    for p in parts: s.paste(p, (x, 0)); x += p.width + gap
    s.save(path); return path
box_on = (LED[0] - 110, LED[1] - 40, LED[0] + 110, FS[1] + 76)
on_img = strip([crop_u(shot("screamer_bypass.png"), box_on), crop_u(src, box_on)], os.path.join(TMP, "screamer_onoff.png"))
# pastille unique : barre de presets au repos (capture par defaut), ligne d'etat pendant un reglage (capture status)
box_bar = (PRESET[0] - 10, PRESET[1] - 10, PRESET[0] + PRESET[2] + 10, PRESET[1] + PRESET[3] + 10)
bar_img = os.path.join(TMP, "screamer_bar.png")
_a = crop_u(shot("screamer_default.png").resize(src.size, Image.LANCZOS), box_bar); _b = crop_u(src, box_bar)
_s = Image.new("RGB", (_a.width, _a.height * 2 + 14), (255, 255, 255)); _s.paste(_a, (0, 0)); _s.paste(_b, (0, _a.height + 14)); _s.save(bar_img)

# ---------- couverture : pedale detouree (boitier rouge + jacks), reflet au sol, halo rouge tres doux ----------
# masque de la pedale (boitier + jacks) : canal alpha du fond (1800 px de haut), a la taille de la capture
msk = np.asarray(Image.open(os.path.join(ROOT, "background.png")).getchannel("A").resize(src.size, Image.LANCZOS))
cut = Image.new("RGBA", src.size, (0, 0, 0, 0)); cut.paste(shot("screamer_default.png").resize(src.size, Image.LANCZOS), (0, 0), Image.fromarray(msk))   # pedale au repos (preset)
cut = cut.crop(cut.getbbox())
cw, ch = cut.size
pad = int(cw * 0.16)
canvas = Image.new("RGBA", (cw + 2 * pad, int(ch * 1.30) + pad), (0, 0, 0, 255))
yy, xx = np.mgrid[0:canvas.height, 0:canvas.width].astype(np.float64)
gcx, gcy = canvas.width / 2, pad + ch * 0.45
glow = np.exp(-(((xx - gcx) / (cw * 0.62)) ** 2 + ((yy - gcy) / (ch * 0.48)) ** 2)) * 30
edge = np.clip(np.minimum.reduce([xx, canvas.width - 1 - xx, yy, canvas.height - 1 - yy]) / (pad * 0.9), 0, 1)
glow *= edge ** 2
halo = np.dstack([glow * 0.95, glow * 0.22, glow * 0.18, np.full_like(glow, 255)]).astype(np.uint8)
canvas = Image.alpha_composite(canvas, Image.fromarray(halo, "RGBA"))
refl = cut.transpose(Image.FLIP_TOP_BOTTOM)
ra = np.array(refl).astype(np.float64)
fade = np.clip(1 - np.arange(refl.height) / (refl.height * 0.22), 0, 1) ** 1.6 * 0.22
ra[..., 3] *= fade[:, None]
canvas.alpha_composite(Image.fromarray(ra.astype(np.uint8), "RGBA"), (pad, pad + ch + 6))
canvas.alpha_composite(cut, (pad, pad))
canvas = canvas.crop((0, 0, canvas.width, pad + int(ch * 1.20)))
cover = os.path.join(TMP, "screamer_cover_cutout.png"); canvas.convert("RGB").save(cover)

def img(path, width):
    im = Image.open(path); h = width * im.height / im.width
    return RLImage(path, width=width, height=h)

# ---------- styles ----------
st = {
    "h1": ParagraphStyle("h1", fontName="PopB", fontSize=20, leading=24, textColor=ACC, spaceAfter=8, spaceBefore=4, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="PopM", fontSize=13, leading=17, textColor=DARK, spaceAfter=4, spaceBefore=10, keepWithNext=1),
    "p": ParagraphStyle("p", fontName="Pop", fontSize=9.6, leading=14, textColor=DARK, spaceAfter=5),
    "tip": ParagraphStyle("tip", fontName="Pop", fontSize=9.0, leading=12.4, textColor=DARK, spaceAfter=3),
    "small": ParagraphStyle("small", fontName="Pop", fontSize=8.2, leading=11.5, textColor=GREY),
    "cell": ParagraphStyle("cell", fontName="Pop", fontSize=8.4, leading=11, textColor=DARK),
    "cellb": ParagraphStyle("cellb", fontName="PopM", fontSize=8.4, leading=11, textColor=DARK),
    "cells": ParagraphStyle("cells", fontName="Pop", fontSize=7.8, leading=10, textColor=DARK),
    "cellbs": ParagraphStyle("cellbs", fontName="PopM", fontSize=7.8, leading=10, textColor=DARK),
    "cover": ParagraphStyle("cover", fontName="Title", fontSize=50, leading=56, textColor=colors.white, alignment=TA_CENTER),
    "coversub": ParagraphStyle("coversub", fontName="Pop", fontSize=12, leading=16, textColor=colors.HexColor("#C9BDBC"), alignment=TA_CENTER),
    "coverlang": ParagraphStyle("coverlang", fontName="PopM", fontSize=8.5, leading=11, textColor=ACC_L),
}
def P(t, s="p"): return Paragraph(t, st[s])
def bullets(items, s="p"): return [P("&bull;&nbsp;&nbsp;" + i, s) for i in items]
def table(rows, widths, header=True, small=False):
    data = [[P(c, ("cellbs" if small else "cellb") if (header and r == 0) else ("cells" if small else "cell")) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#E3D3D1")),
             ("TOPPADDING", (0, 0), (-1, -1), 2 if small else 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 2 if small else 3)]
    if header: style += [("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACC)]
    t.setStyle(TableStyle(style)); return t

# ---------- donnees (identiques au code livre : PluginProcessor.cpp) ----------
FACTORY = [("Classic TS9", 5.0, 5.0, 5.0), ("Texas Blues", 2.5, 6.0, 7.5), ("Metal Boost (7 strings)", 0.0, 6.0, 10.0),
           ("Edge of Breakup", 1.5, 5.0, 6.0), ("Rhythm Crunch", 6.0, 5.0, 5.0), ("Singing Lead", 8.5, 6.0, 5.5),
           ("Warm & Round", 4.0, 3.0, 6.0), ("Bright Humbucker", 5.0, 7.5, 5.5), ("Full Drive", 10.0, 5.0, 4.5),
           ("Clean Mid Boost", 0.0, 5.0, 6.5)]
FACT_DESC = {
 "fr": ["Tout à midi : le réglage de référence, overdrive chaude, médiums en avant, à peu près au niveau du son direct.",
        "Peu de drive, beaucoup de level, tone un peu ouvert : pousse un ampli clair vers une saturation chantante.",
        "Drive à zéro, Level à fond, Tone vers 13 h : l'astuce classique du metal. La pédale sature à peine mais retire le grave avant l'ampli : les palm mutes d'une 7 cordes en Sol restent serrés et précis.",
        "Un crunch léger qui s'éclaircit quand on joue doucement ou qu'on baisse le volume de la guitare.",
        "Drive après midi : un crunch rythmique épais mais défini.",
        "Beaucoup de drive, tone un peu ouvert : sustain doux, médiums devant, pour les solos.",
        "Tone vers 10 h : chaud et rond, calme les micros simples brillants.",
        "Tone vers 14 h : ouvre des humbuckers sombres.",
        "Drive à fond : le sustain maximum du circuit, toujours plus doux qu'une distorsion.",
        "Drive à zéro : presque clair, seulement la bosse de médiums du TS et le grave resserré."]}

T = {
"fr": dict(
 lang="FRANÇAIS", sub="Overdrive",
 intro_t="1. Présentation",
 intro=["<b>SCREAMER</b> est un plugin NINE HANDS | DSP inspiré de l'<b>Ibanez TS9 Tube Screamer</b> (1982), l'overdrive verte qui a défini, avec sa sœur la TS808, le son « Tube Screamer » : une saturation chaude et douce, médiums en avant et grave serré, utilisée pour pousser les amplis du blues au metal.",
        "Le circuit est reproduit <b>étage par étage</b> avec les valeurs de l'original : tampon d'entrée, étage d'écrêtage autour de la première moitié de l'ampli op JRC4558, étage de tonalité autour de la seconde moitié, potentiomètre Level et tampon de sortie de la TS9. L'étage d'écrêtage est résolu à chaque échantillon (intégration par la méthode des trapèzes et méthode de Newton sur l'équation de Shockley des deux diodes 1S1588), en sur-échantillonnage x4. Rien n'est ajouté par-dessus : la bosse de médiums, l'écrêtage doux et la façon dont la pédale s'éclaircit viennent des composants eux-mêmes.",
        "Pourquoi ce son : dans l'étage d'écrêtage, seules les fréquences au-dessus d'environ <b>720 Hz</b> (4,7 k + 47 nF vers la masse) sont amplifiées ; le grave passe avec un gain de 1, propre. Les deux diodes sont dans la boucle de contre-réaction de l'ampli op : la sortie est le signal propre <i>plus</i> les médiums écrêtés en douceur, une saturation « à lampes » qui garde la dynamique du jeu. Un passe-bas à 723 Hz (1 k + 220 nF) adoucit ensuite l'aigu, et l'étage de tonalité actif rend autant d'aigu que vous voulez.",
        "Le visuel est un design original NINE HANDS | DSP : la disposition des potards de la TS9 (Drive et Level en haut, Tone plus petit au milieu) sur un boîtier rouge sang de bœuf imprimé d'un grand visage qui crie, passant sous toutes les commandes et inscriptions ; Screamer n'est pas affilié à Ibanez, et « Tube Screamer » et « TS9 » ne servent qu'à décrire le circuit reproduit."],
 inst_t="2. Installation",
 inst=[("Windows", "Cliquez sur le bouton <b>Télécharger Windows</b> de la page GitHub Nine-Hands-Dsp/screamer (il donne toujours la dernière version), décompressez <b>Screamer-VST3-Windows.zip</b> et copiez le dossier <b>Screamer.vst3</b> dans <b>C:\\Program Files\\Common Files\\VST3</b>."),
       ("macOS", "Cliquez sur <b>Télécharger macOS</b>, décompressez <b>Screamer-VST3-macOS.zip</b> et copiez <b>Screamer.vst3</b> dans <b>~/Bibliothèque/Audio/Plug-Ins/VST3</b>. Si macOS le bloque, tapez <b>xattr -cr ~/Library/Audio/Plug-Ins/VST3/Screamer.vst3</b> dans le Terminal. Le binaire est universel (Apple Silicon et Intel)."),
       ("Reaper", "Options &gt; Préférences &gt; Plug-ins &gt; VST &gt; <b>Re-scan</b>. Le plugin apparaît sous le nom <b>Screamer (NINE HANDS | DSP)</b>. Pour le piloter avec des footswitchs et pédales d'expression MIDI, la piste doit recevoir le MIDI du contrôleur (armement ou monitoring d'entrée, entrée MIDI réglée sur votre appareil, par exemple la M-Vave Chocolate Plus).")],
 ov_t="3. Vue d'ensemble de l'interface",
 ov_rows=[["#", "Commande", "Rôle"],
   ["1", "DRIVE", "Quantité de saturation. Glisser vers le haut / le bas, molette, double-clic = midi, clic droit = MIDI Learn (valable pour toutes les commandes)."],
   ["2", "TONE", "Aigus : sombre à gauche, brillant à droite."],
   ["3", "LEVEL", "Volume de sortie."],
   ["4", "Presets / ligne d'état", "Une seule pastille : barre de presets au repos (flèches = précédent / suivant, clic sur le nom = menu) ; ligne d'état à la place tant qu'un réglage bouge."],
   ["5", "LED", "Rouge = effet actif, éteinte = bypass."],
   ["6", "Footswitch", "Effet actif / bypass."],
   ["7", "OUT", "Jack de sortie."],
   ["8", "IN", "Jack d'entrée."]],
 on_cap="Bypass, puis effet actif : LED rouge, la façade reçoit sa lumière.",
 ctl_t="4. Les commandes en détail",
 ctl=[("DRIVE", "Le potentiomètre Drive de 500 k (courbe log) de la TS9, en série avec 51 k dans la contre-réaction de l'étage d'écrêtage. Au minimum, le gain des médiums est déjà d'environ 12 (+21 dB) : avec une guitare normale la pédale craque déjà un peu et reste claire quand on joue doucement. Au maximum, le gain atteint environ 118 (+41 dB) et le condensateur de 51 pF aux bornes des diodes coupe l'écrêtage au-dessus d'environ 5,7 kHz : la saturation devient plus douce, pas plus grésillante. Le grave, sous 720 Hz, n'est jamais amplifié : même à fond il reste serré. Comme l'écrêtage est doux et que le signal propre passe avec lui, la saturation réagit fortement à l'attaque et au volume de la guitare."),
      ("TONE", "L'étage de tonalité actif de la TS9 avec ses vraies valeurs (pot 20 k, 220 ohms + 220 nF du curseur à la masse, 1 k / 220 nF à l'entrée, 1 k de contre-réaction). Au minimum, il ajoute une seconde pente sur l'aigu (environ −19 dB à 4 kHz : sombre et rond) ; au maximum, il rend l'aigu (environ −2,5 dB à 4 kHz : ouvert et tranchant). Sur la pédale, l'essentiel de la variation se fait dans le dernier tiers de la course ; sur Screamer la courbe du potard est répartie pour que chaque cran change l'aigu de la même quantité, entre exactement les mêmes extrêmes."),
      ("LEVEL", "Le potentiomètre Level de 100 k (courbe log) de la TS9 : 0 = coupé. Avec Drive et Tone à midi et une guitare qui crête à 0,1 – 0,15 V (environ −20 à −16 dBFS), midi donne à peu près le niveau de la guitare en bypass ; à fond, environ +14 à +16 dB, de quoi attaquer fort l'entrée d'un ampli. Il n'y a pas de plafond à 0 dBFS : comme sur la pédale, la sortie peut dépasser 0 dBFS (le DAW calcule en virgule flottante), jusqu'à l'excursion des amplis op de la pédale en 9 V, environ ±3,4 V (≈ +10,6 dBFS) ; un simulateur d'ampli placé après Screamer est donc poussé aussi fort qu'un vrai ampli.")],
 fs_t="5. Footswitch, LED et noise gate",
 fs=["<b>Footswitch</b> : il bascule dès l'appui et le bouton s'assombrit tant qu'on appuie. En bypass, le signal sec passe, aligné dans le temps sur la latence du sur-échantillonnage annoncée au DAW (la TS9 a un bypass bufferisé, transparent).",
     "<b>LED</b> : rouge quand l'effet est actif, en fondu ; la façade autour et le flanc de l'écrou du footswitch reçoivent sa lumière.",
     "<b>Noise gate</b> (clic droit &gt; Noise gate) : <b>Off</b> par défaut, comme la pédale d'origine, ou Light, Medium, Strong pour des micros bruyants. N'agit que sur l'effet."],
 midi_t="6. MIDI",
 midi_intro=["Toutes les commandes se pilotent depuis un contrôleur MIDI (footswitchs, pédales d'expression, potards). Screamer écoute tous les canaux MIDI. <b>Aucun CC n'est assigné d'office</b> : vous choisissez chacun avec le <b>MIDI Learn</b>."],
 midi_hdr=["Commande", "Assignation", "Type"],
 midi=[["Drive", "MIDI Learn", "Continu (0-127 = toute la course)"], ["Tone", "MIDI Learn", "Continu"], ["Level", "MIDI Learn", "Continu"],
       ["Footswitch", "MIDI Learn", "À accrochage (127 = on / 0 = off) ou momentané (bascule à chaque appui)"]],
 learn=["<b>MIDI Learn</b> : clic droit sur une commande, choisissez <b>MIDI Learn: &lt;nom&gt; (CC n)</b> (<b>—</b> si rien n'est assigné), puis bougez la pédale d'expression ou appuyez sur le bouton MIDI. La ligne d'état affiche <b>MIDI LEARN: move a control for Drive</b>, puis confirme pendant 2 secondes, par ex. <b>Drive = CC 64</b>. <b>Clear MIDI</b> retire une assignation ; clic droit &gt; MIDI &gt; <b>Clear all MIDI assignments</b> les retire toutes. Les assignations sont sauvegardées avec le projet.",
        "<b>Pédales d'expression</b> : les mouvements ne sont jamais saccadés. Screamer rejoint chaque nouvelle valeur par une rampe sur le temps mesuré entre deux messages ; la course réelle de votre pédale est apprise automatiquement (une pédale qui n'envoie que 2 à 116 atteint quand même exactement 0 et 100 %). Pour un potard sur un CC de 0 à 31, le CC n+32 est lu comme sa partie fine (14 bits).",
        "<b>Footswitch MIDI</b> : à accrochage (par défaut) ou momentané, clic droit &gt; Settings. <b>Program Change 1 à 10</b> : rappel des presets usine. Tous les paramètres sont aussi automatisables dans le DAW."],
 win_t="7. Fenêtre",
 win=["Screamer utilise le format pédale simple de NINE HANDS | DSP : la fenêtre montre la pédale seule, plein cadre (visuel de 1235 × 1800 px), textes et logo dessinés en vectoriel, nets à toutes les tailles, elle s'ouvre à 60 % et ne peut jamais être réduite en dessous. Clic droit &gt; <b>Plugin size</b> : <b>60 %</b>, <b>75 %</b> ou <b>100 %</b>, « (default) » indiquant la taille par défaut ; <b>Default size (new windows)</b> choisit la taille d'ouverture de toutes les nouvelles fenêtres de Screamer (réglage commun à toutes les instances) et redimensionne aussitôt la fenêtre courante. Vous pouvez aussi tirer le coin en bas à droite jusqu'à 150 % (les proportions sont conservées).",
      "La <b>barre de presets</b> et la <b>ligne d'état</b> partagent la même pastille. Au repos, elle affiche le preset (ou <i>Edited</i>) avec ses flèches. Dès qu'un réglage bouge (souris, molette, automation, MIDI), la ligne d'état prend sa place en fondu et affiche la valeur en direct (par ex. <i>DRIVE 64 %</i>) ou les messages du MIDI Learn ; 2,5 s après le dernier mouvement, elle s'efface et la barre de presets revient. Un clic sur la pastille la fait revenir tout de suite.",
      "Les menus clic droit s'ouvrent à l'endroit du clic."],
 bar_cap="Barre de presets au repos, ligne d'état pendant un réglage.",
 pre_t="8. Presets",
 pre=["Utilisez les flèches de la barre de presets, cliquez sur son nom, faites un clic droit n'importe où, ou passez par le menu de presets de votre DAW. Clic droit &gt; <b>Save user preset</b> enregistre jusqu'à 9 presets personnels."],
 fac_hdr=["PC", "Preset", "Drive / Tone / Level (%)", "Description"],
 tips_t="9. Conseils d'utilisation",
 tips=["Dans Reaper, placez Screamer <b>avant</b> votre simulateur d'ampli (par exemple avant Ampire, le plugin d'ampli NINE HANDS | DSP pour captures NAM, suivi d'Impulse pour l'IR de baffle), comme avec la vraie pédale devant un ampli.",
       "L'usage le plus célèbre : <b>Drive bas, Level haut</b> devant un ampli déjà saturé (preset <i>Metal Boost</i>). La pédale resserre le grave et pousse les médiums, l'ampli fait la saturation. Idéal pour une 7 cordes en Sol ou des accordages plus bas.",
       "Devant un ampli clair, montez le Drive et gardez le Level vers midi : c'est une overdrive, pas une distorsion ; pour plus de gain, empilez-la avec un ampli crunch.",
       "Baissez le volume de la guitare pour éclaircir le son : l'écrêtage doux le suit de près."],
 tech_t="10. Caractéristiques techniques",
 tech=[["Format", "VST3 (Windows 64 bits, macOS universel)"], ["Canaux", "Mono ou stéréo"],
       ["Latence", "32 échantillons (filtre de sur-échantillonnage), annoncée au DAW"],
       ["Circuit", "tampon d'entrée (≈18 Hz), étage d'écrêtage (4,7 k + 47 nF, 51 k + Drive 500 k log, 51 pF, 2 × 1S1588), étage de tonalité (1 k / 220 nF, pot 20 k, 220 ohms + 220 nF, 1 k), Level 100 k log, tampon de sortie TS9"],
       ["Gain (médiums)", "environ +21 dB (Drive à 0) à +41 dB (Drive à 10), écrêtage doux par diodes"],
       ["Level", "coupé à environ +15 dB ; midi ≈ niveau de la guitare avec Drive / Tone à midi ; pas de plafond à 0 dBFS (excursion de la pédale ±3,4 V)"],
       ["Traitement", "étage d'écrêtage résolu à chaque échantillon (trapèzes + Newton), sur-échantillonnage x4, étage de tonalité exact du 2e ordre (bilinéaire), paramètres lissés"],
       ["Processeur", "environ 5 à 10 % d'un cœur à 48 kHz (stéréo), selon l'ordinateur"],
       ["MIDI", "tous les canaux ; MIDI Learn sur les 4 commandes (rien d'assigné par défaut), CC 14 bits, Program Change 1-10"],
       ["Fenêtre", "Plugin size 60 % / 75 % / 100 %, taille par défaut des nouvelles fenêtres au choix (60 % au départ), jusqu'à 150 %, jamais sous 60 % ; anti-gel v2 sous Windows"]]),
}

COVER_TEXT = {}
W = A4[0] - 36 * mm
LOGO_PNG = os.path.join(TMP, "nine_hands_logo_blanc.png")
import subprocess
subprocess.run(["rsvg-convert", "-w", "1200", os.path.join(ROOT, "NineHandsLogo.svg"), "-o", LOGO_PNG], check=True)
def section(lang):
    t = T[lang]; f = []
    f.append(NextPageTemplate("p"))
    COVER_TEXT.update(lang=t["lang"], sub=t["sub"])      # couverture dessinee a positions fixes (cover_bg)
    f.append(Spacer(1, 1)); f.append(PageBreak())
    f.append(P(t["intro_t"], "h1")); f += [P(x) for x in t["intro"]]
    f.append(P(t["inst_t"], "h1"))
    for h, x in t["inst"]: f.append(P(h, "h2")); f.append(P(x))
    f.append(PageBreak())
    f.append(P(t["ov_t"], "h1"))
    ov = Table([[[img(annotated, 80 * mm)],
                 [table(t["ov_rows"], [9 * mm, 27 * mm, W - 96 * mm - 36 * mm]), Spacer(1, 6 * mm), img(on_img, 62 * mm), P(t["on_cap"], "small")]]],
               colWidths=[96 * mm, W - 96 * mm])
    ov.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    f.append(ov); f.append(PageBreak())
    f.append(P(t["ctl_t"], "h1"))
    for h, x in t["ctl"]: f.append(P(h, "h2")); f.append(P(x))
    f.append(P(t["fs_t"], "h1")); f += bullets(t["fs"])
    f.append(P(t["midi_t"], "h1")); f += [P(x) for x in t["midi_intro"]]
    f.append(KeepTogether([table([t["midi_hdr"]] + t["midi"], [36 * mm, 26 * mm, W - 62 * mm])]))
    f.append(Spacer(1, 2 * mm)); f += bullets(t["learn"])
    f.append(P(t["win_t"], "h1")); f.append(P(t["win"][0]))
    wt = Table([[[P(t["win"][1]), P(t["win"][2])], [img(bar_img, 66 * mm), P(t["bar_cap"], "small")]]], colWidths=[W - 70 * mm, 70 * mm])
    wt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (0, 0), 0)]))
    f.append(wt)
    f.append(P(t["pre_t"], "h1")); f += [P(x) for x in t["pre"]]
    rows = [t["fac_hdr"]]
    for i, (n, d, tn, lv) in enumerate(FACTORY):
        rows.append([str(i + 1), "<b>" + n.replace("&", "&amp;") + "</b>", f"{round(d * 10)} / {round(tn * 10)} / {round(lv * 10)}", FACT_DESC[lang][i]])
    f.append(table(rows, [8 * mm, 32 * mm, 24 * mm, W - 64 * mm], small=True))
    # conseils + caracteristiques ensemble : le tableau ne se retrouve jamais seul sur une page
    f.append(KeepTogether([P(t["tips_t"], "h1")] + bullets(t["tips"], "tip") +
                          [P(t["tech_t"], "h1"), table(t["tech"], [28 * mm, W - 28 * mm], header=False, small=True)])); f.append(Spacer(1, 4 * mm))
    f.append(PageBreak())
    return f

def deco(c, doc):
    c.saveState()
    c.setFillColor(DARK); c.rect(0, A4[1] - 6 * mm, A4[0], 6 * mm, stroke=0, fill=1)
    c.setFillColor(ACC); c.rect(0, A4[1] - 6.8 * mm, A4[0], 0.8 * mm, stroke=0, fill=1)
    c.setFont("Pop", 7.5); c.setFillColor(GREY)
    c.drawString(18 * mm, 10 * mm, "Screamer (NINE HANDS | DSP) · v" + VERSION)
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, str(doc.page))
    c.restoreState()

doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                      title="SCREAMER - Notice v" + VERSION, author="NINE HANDS | DSP")
# ---- Couverture « minimale » (modele 6, valide nov. 2026) : gabarit fixe commun a toutes les notices ----
# Mesures en mm depuis le HAUT de la page A4, sauf le logo et le bandeau (depuis le bas). Aucun autre element.
COVER_NAME = "SCREAMER"
PEDAL_H, PEDAL_MAXW, PEDAL_TOP = 82 * mm, 115 * mm, 84 * mm      # pedale (boitier + jacks, sans reflet) centree horizontalement
LANG_TOP = 18 * mm                                               # « FRANÇAIS » centre, Poppins Medium 8,5 pt, accent clair
NAME_TOP, NAME_PT = 194 * mm, 30                                 # nom : Barlow Condensed ExtraBold 30 pt, approche 0,5 x corps
SUB_TOP, SUB_PT = 208 * mm, 10                                   # mention courte : Poppins 10 pt, approche 1,5 pt, gris clair
LOGO_W, LOGO_BOTTOM = 38 * mm, 22 * mm                           # logo blanc centre en bas
BAND_H = 3 * mm                                                  # bandeau couleur d'accent en BAS de page
def cover_bg(c, doc):
    c.saveState(); c.setFillColor(colors.black); c.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
    c.setFillColor(ACC); c.rect(0, 0, A4[0], BAND_H, stroke=0, fill=1)
    def line(text, top, font, size, cs, col):
        w = pdfmetrics.stringWidth(text, font, size) + cs * (len(text) - 1)
        t = c.beginText((A4[0] - w) / 2, A4[1] - top - size * 0.8); t.setFont(font, size); t.setCharSpace(cs)
        t.setFillColor(col); t.textOut(text); c.drawText(t)
    line(COVER_TEXT["lang"], LANG_TOP, "PopM", 8.5, 0, ACC_L)
    ci = Image.open(cover); iw, ih = ci.size
    cw_ = iw / 1.32; ch_ = (ih - int(cw_ * 0.16)) / 1.2; pad_ = int(cw_ * 0.16)     # geometrie de screamer_cover_cutout.png
    kk = min(PEDAL_H / ch_, PEDAL_MAXW / cw_)
    dw, dh = iw * kk, ih * kk
    y0 = A4[1] - (PEDAL_TOP + (PEDAL_H - ch_ * kk) / 2) + pad_ * kk
    c.drawImage(cover, (A4[0] - dw) / 2, y0 - dh, dw, dh)
    line(COVER_NAME, NAME_TOP - NAME_PT * 0.02, "Title", NAME_PT, NAME_PT * 0.5, colors.white)
    line(COVER_TEXT["sub"], SUB_TOP, "Pop", SUB_PT, 1.5, colors.HexColor("#BDC4B8"))
    lw, lh = Image.open(LOGO_PNG).size
    c.drawImage(LOGO_PNG, (A4[0] - LOGO_W) / 2, LOGO_BOTTOM, LOGO_W, LOGO_W * lh / lw, mask="auto")
    c.restoreState()
doc.addPageTemplates([PageTemplate(id="cover", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="fc")], onPage=cover_bg),
                      PageTemplate(id="p", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")], onPage=deco)])
fr = section("fr")              # notices en francais uniquement (couverture noire FRANCAIS)
doc.build(fr[:-1])
print(OUT)
