# SCREAMER (NINE HANDS | DSP) - notice PDF bilingue (anglais puis francais), illustree avec le rendu reel du plugin.
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
VERSION = "1.3.1"
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
         (4, STATUS[0] + 8, STATUS[1] - 14), (5, PRESET[0] - 22, PRESET[1] + 18), (6, LED[0] + 34, LED[1]),
         (7, FS[0] + 80, FS[1]), (8, LAY["jackL"] + 16, JACK_Y - 66), (9, LAY["jackR"] - 16, JACK_Y - 66)]
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
bar_img = os.path.join(TMP, "screamer_bar.png"); crop_u(src, (STATUS[0] - 15, STATUS[1] - 12, STATUS[0] + STATUS[2] + 15, PRESET[1] + PRESET[3] + 10)).save(bar_img)

# ---------- couverture : pedale detouree (boitier rouge + jacks), reflet au sol, halo rouge tres doux ----------
# masque de la pedale (boitier + jacks) : canal alpha du fond (1800 px de haut), a la taille de la capture
msk = np.asarray(Image.open(os.path.join(ROOT, "background.png")).getchannel("A").resize(src.size, Image.LANCZOS))
cut = Image.new("RGBA", src.size, (0, 0, 0, 0)); cut.paste(src, (0, 0), Image.fromarray(msk))
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
 "en": ["Everything at noon: the reference setting, warm mid-forward overdrive at about unity level.",
        "Little drive, a lot of level, tone a bit open: pushes a clean amp into a vocal, singing breakup.",
        "Drive at zero, Level fully up, Tone around 1 o'clock: the classic metal trick. The pedal hardly distorts but cuts the low end before the amp, so palm mutes on a 7-string in G stay tight and articulate.",
        "Barely-there crunch that cleans up when you play softly or turn down the guitar.",
        "Drive past noon: a thick but defined rhythm crunch.",
        "High drive, tone slightly open: smooth sustain with the mids in front for solos.",
        "Tone around 10 o'clock: warm and round, tames bright single-coil pickups.",
        "Tone around 2 o'clock: opens up dark humbuckers.",
        "Drive full up: the maximum sustain of the circuit, still softer than a distortion pedal.",
        "Drive at zero: almost clean, just the TS mid hump and the tightened low end."],
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
"en": dict(
 lang="ENGLISH", sub="Overdrive &nbsp;·&nbsp; VST3 for Windows and macOS", ver="User manual &nbsp;·&nbsp; version " + VERSION,
 intro_t="1. Introduction",
 intro=["<b>SCREAMER</b> is a NINE HANDS | DSP plugin modelled on the <b>Ibanez TS9 Tube Screamer</b> (1982), the green overdrive that, with its TS808 sibling, defined the mid-forward \"Tube Screamer\" sound: a warm, smooth overdrive with a hump in the mids and a tight low end, loved for pushing amps from blues to metal.",
        "The circuit is modelled <b>stage by stage</b> with the values of the original: the input buffer, the clipping stage built around the first half of the JRC4558 op-amp, the tone stage built around the second half, the Level pot and the TS9 output buffer. The clipping stage is solved at every sample (trapezoidal integration and Newton's method on the Shockley equation of the two 1S1588 diodes), at 4x oversampling. Nothing is added on top: the mid hump, the soft clipping and the way the pedal cleans up come from the components themselves.",
        "Why it sounds like that: in the clipping stage, only the frequencies above about <b>720 Hz</b> (4.7 k + 47 nF to ground) are amplified; the low end goes through at unity gain, clean. The two diodes sit in the op-amp's feedback loop, so the output is the clean signal <i>plus</i> the softly clipped mids: a smooth, \"tube-like\" overdrive that keeps your picking dynamics. A 723 Hz low-pass (1 k + 220 nF) then softens the top, and the active tone stage brings back as much treble as you want.",
        "The visual is an original NINE HANDS | DSP design: the knob layout of the TS9 (Drive and Level on top, a smaller Tone in the middle) on an oxblood enclosure printed with a large screaming face, which runs under all the controls and lettering; Screamer is not affiliated with Ibanez, and \"Tube Screamer\" and \"TS9\" are only used to describe the circuit it models."],
 inst_t="2. Installation",
 inst=[("Windows", "Download the <b>Screamer-VST3-Windows</b> artifact from the Actions tab of the GitHub repository Nine-Hands-Dsp/Screamer, unzip it and copy the <b>Screamer.vst3</b> folder into <b>C:\\Program Files\\Common Files\\VST3</b>."),
       ("macOS", "Download <b>Screamer-VST3-macOS</b>, unzip it and copy <b>Screamer.vst3</b> into <b>~/Library/Audio/Plug-Ins/VST3</b>. If macOS blocks it, run <b>xattr -cr ~/Library/Audio/Plug-Ins/VST3/Screamer.vst3</b> in the Terminal. The binary is universal (Apple Silicon and Intel)."),
       ("Reaper", "Options &gt; Preferences &gt; Plug-ins &gt; VST &gt; <b>Re-scan</b>. The plugin appears as <b>Screamer (NINE HANDS | DSP)</b>. To control it from MIDI footswitches and expression pedals, the track must receive MIDI from the controller (record-arm or input monitoring, MIDI input set to your device, e.g. the M-Vave Chocolate Plus).")],
 ov_t="3. Interface overview",
 ov_rows=[["#", "Control", "Role"],
   ["1", "DRIVE", "Amount of overdrive. Drag up / down, mouse wheel, double-click = noon, right-click = MIDI Learn (true for every control)."],
   ["2", "TONE", "Treble: dark to the left, bright to the right."],
   ["3", "LEVEL", "Output volume."],
   ["4", "Screen", "Setting of the control you just moved; appears when something moves."],
   ["5", "Preset bar", "Arrows = previous / next factory preset, click on the name = preset menu."],
   ["6", "LED", "Red = effect on, off = bypass."],
   ["7", "Footswitch", "Effect on / bypass."],
   ["8", "OUT", "Output jack."],
   ["9", "IN", "Input jack."]],
 on_cap="Bypass, then effect on: red LED, the panel catches its light.",
 ctl_t="4. Controls in detail",
 ctl=[("DRIVE", "The 500 k audio-taper Drive pot of the TS9, in series with 51 k in the feedback loop of the clipping stage. Fully down, the gain of the mids is already about 12 (+21 dB): with a normal guitar the pedal already crunches a little and stays clean on soft playing. Fully up, the gain reaches about 118 (+41 dB) and the 51 pF capacitor across the diodes rolls the clipping off above about 5.7 kHz, so the drive gets smoother, not fizzier. The low end, below 720 Hz, is never amplified: even fully up the bass stays tight. Because the clipping is soft and the clean signal goes through with it, the drive reacts strongly to your picking and to your guitar's volume knob."),
      ("TONE", "The active tone stage of the TS9 with its real values (20 k pot, 220 ohms + 220 nF from the wiper to ground, 1 k / 220 nF at the input, 1 k feedback). Fully down, it adds a second treble roll-off (about −19 dB at 4 kHz: dark and round); fully up, it brings the treble back (about −2.5 dB at 4 kHz: open and cutting). On the hardware most of the change happens in the last third of the travel; on Screamer the pot curve is spread so that each step of the knob changes the treble by the same amount, between exactly the same two extremes."),
      ("LEVEL", "The 100 k audio-taper Level pot of the TS9: 0 = muted. With Drive and Tone at noon and a guitar peaking at 0.1 to 0.15 V (about −20 to −16 dBFS), noon gives roughly the level of the bypassed guitar; fully up gives about +14 to +16 dB, enough to slam the front of an amp. There is no 0 dBFS ceiling: like the hardware, the output can go above 0 dBFS (the DAW works in floating point), up to the swing of the pedal's 9 V op-amps, about ±3.4 V (≈ +10.6 dBFS), so an amp simulator placed after Screamer is pushed as hard as a real amp.")],
 fs_t="5. Footswitch, LED and noise gate",
 fs=["<b>Footswitch</b>: it switches as soon as you press it and the cap darkens while held. In bypass, the dry signal is passed through, time-aligned with the oversampling latency reported to the DAW (the TS9 has a buffered bypass, which is transparent).",
     "<b>LED</b>: red when the effect is on, with a fade; the panel around it and the side of the footswitch nut catch its light.",
     "<b>Noise gate</b> (right-click &gt; Noise gate): <b>Off</b> by default, like the original pedal, or Light, Medium, Strong for noisy pickups. Acts on the effect only."],
 midi_t="6. MIDI",
 midi_intro=["Every control can be driven from a MIDI controller (footswitches, expression pedals, knobs). Screamer listens on all MIDI channels. <b>No CC is assigned out of the box</b>: you choose each one with <b>MIDI Learn</b>."],
 midi_hdr=["Control", "Assignment", "Type"],
 midi=[["Drive", "MIDI Learn", "Continuous (0-127 = full travel)"], ["Tone", "MIDI Learn", "Continuous"], ["Level", "MIDI Learn", "Continuous"],
       ["Footswitch", "MIDI Learn", "Latching (127 = on / 0 = off) or momentary (toggle on each press)"]],
 learn=["<b>MIDI Learn</b>: right-click a control, choose <b>MIDI Learn: &lt;name&gt; (CC n)</b> (<b>—</b> when nothing is assigned), then move your expression pedal or press the MIDI button. The screen shows <b>MIDI LEARN: move a control for Drive</b>, then confirms for 2 seconds, e.g. <b>Drive = CC 64</b>. <b>Clear MIDI</b> removes an assignment; right-click &gt; MIDI &gt; <b>Clear all MIDI assignments</b> removes them all. Assignments are saved with the project.",
        "<b>Expression pedals</b>: movements are never stepped. Screamer ramps to each new value over the time between two messages; the real travel of your pedal is learnt automatically (a pedal sending only 2 to 116 still reaches exactly 0 and 100 %). For a knob on CC 0 to 31, CC n+32 is read as its fine 14-bit part.",
        "<b>MIDI footswitch</b>: latching (default) or momentary, right-click &gt; Settings. <b>Program Change 1 to 10</b> recall the factory presets. All parameters can also be automated in the DAW."],
 win_t="7. Window",
 win=["Screamer uses the single pedal format of NINE HANDS | DSP: the window shows the pedal alone, full frame (1800 px high artwork, width in the pedal's own proportions), it opens at 60 % and can never be made smaller. Right-click &gt; <b>Plugin size</b>: <b>60 %</b>, <b>75 %</b> or <b>100 %</b>, \"(default)\" marking the default size; <b>Default size (new windows)</b> chooses the size at which every new Screamer window opens (one setting shared by all instances) and resizes the current one at once. You can also drag the bottom-right corner up to 150 % (proportions are kept).",
      "The <b>screen</b> shows the setting of the knob you just moved (e.g. <i>DRIVE 64 %</i>); it appears when a setting moves and fades out after 2.5 s. It also shows the MIDI Learn messages. The <b>preset bar</b> under it always shows the current preset (or <i>Edited</i>)."],
 bar_cap="Screen and preset bar.",
 pre_t="8. Presets",
 pre=["Use the arrows of the preset bar, click its name, right-click anywhere, or use the preset menu of your DAW. Right-click &gt; <b>Save user preset</b> stores up to 9 presets of your own."],
 fac_hdr=["PC", "Preset", "Drive / Tone / Level (%)", "Description"],
 tips_t="9. Tips",
 tips=["In Reaper place Screamer <b>before</b> your amp simulator (for example before Ampire, the NINE HANDS | DSP amp plugin for NAM captures, followed by Impulse for the cabinet IR), as you would with the real pedal in front of an amp.",
       "The most famous use: <b>Drive low, Level high</b> in front of an amp that is already overdriven (preset <i>Metal Boost</i>). The pedal tightens the low end and pushes the mids, the amp does the distortion. Ideal for a 7-string in G or lower tunings.",
       "In front of a clean amp, raise Drive and keep Level around noon: it is an overdrive, not a distortion; for more gain, stack it into a crunchy amp.",
       "Roll back your guitar's volume knob to clean up the sound: the soft clipping follows it closely."],
 tech_t="10. Specifications",
 tech=[["Format", "VST3 (Windows 64-bit, macOS universal)"], ["Channels", "Mono or stereo"],
       ["Latency", "32 samples (oversampling filter), reported to the DAW"],
       ["Circuit", "input buffer (≈18 Hz), clipping stage (4.7 k + 47 nF, 51 k + Drive 500 k A, 51 pF, 2 × 1S1588), tone stage (1 k / 220 nF, 20 k pot, 220 ohms + 220 nF, 1 k), Level 100 k A, TS9 output buffer"],
       ["Gain (mids)", "about +21 dB (Drive at 0) to +41 dB (Drive at 10), soft diode clipping"],
       ["Level", "muted to about +15 dB; noon ≈ guitar level with Drive / Tone at noon; no 0 dBFS ceiling (pedal swing ±3.4 V)"],
       ["Processing", "clipping stage solved at each sample (trapezoidal + Newton), 4x oversampling, exact 2nd-order tone stage (bilinear), smoothed parameters"],
       ["CPU", "about 5 to 10 % of one core at 48 kHz (stereo), depending on the computer"],
       ["MIDI", "all channels; MIDI Learn on the 4 controls (nothing assigned by default), 14-bit CC, Program Change 1-10"],
       ["Window", "Plugin size 60 % / 75 % / 100 %, default size of new windows to choose (60 % at first), up to 150 %, never smaller than 60 %; anti-freeze v2 under Windows"]]),
"fr": dict(
 lang="FRANÇAIS", sub="Overdrive &nbsp;·&nbsp; VST3 pour Windows et macOS", ver="Notice d'utilisation &nbsp;·&nbsp; version " + VERSION,
 intro_t="1. Présentation",
 intro=["<b>SCREAMER</b> est un plugin NINE HANDS | DSP inspiré de l'<b>Ibanez TS9 Tube Screamer</b> (1982), l'overdrive verte qui a défini, avec sa sœur la TS808, le son « Tube Screamer » : une saturation chaude et douce, médiums en avant et grave serré, utilisée pour pousser les amplis du blues au metal.",
        "Le circuit est reproduit <b>étage par étage</b> avec les valeurs de l'original : tampon d'entrée, étage d'écrêtage autour de la première moitié de l'ampli op JRC4558, étage de tonalité autour de la seconde moitié, potentiomètre Level et tampon de sortie de la TS9. L'étage d'écrêtage est résolu à chaque échantillon (intégration par la méthode des trapèzes et méthode de Newton sur l'équation de Shockley des deux diodes 1S1588), en sur-échantillonnage x4. Rien n'est ajouté par-dessus : la bosse de médiums, l'écrêtage doux et la façon dont la pédale s'éclaircit viennent des composants eux-mêmes.",
        "Pourquoi ce son : dans l'étage d'écrêtage, seules les fréquences au-dessus d'environ <b>720 Hz</b> (4,7 k + 47 nF vers la masse) sont amplifiées ; le grave passe avec un gain de 1, propre. Les deux diodes sont dans la boucle de contre-réaction de l'ampli op : la sortie est le signal propre <i>plus</i> les médiums écrêtés en douceur, une saturation « à lampes » qui garde la dynamique du jeu. Un passe-bas à 723 Hz (1 k + 220 nF) adoucit ensuite l'aigu, et l'étage de tonalité actif rend autant d'aigu que vous voulez.",
        "Le visuel est un design original NINE HANDS | DSP : la disposition des potards de la TS9 (Drive et Level en haut, Tone plus petit au milieu) sur un boîtier rouge sang de bœuf imprimé d'un grand visage qui crie, passant sous toutes les commandes et inscriptions ; Screamer n'est pas affilié à Ibanez, et « Tube Screamer » et « TS9 » ne servent qu'à décrire le circuit reproduit."],
 inst_t="2. Installation",
 inst=[("Windows", "Téléchargez l'artefact <b>Screamer-VST3-Windows</b> dans l'onglet Actions du dépôt GitHub Nine-Hands-Dsp/Screamer, décompressez-le et copiez le dossier <b>Screamer.vst3</b> dans <b>C:\\Program Files\\Common Files\\VST3</b>."),
       ("macOS", "Téléchargez <b>Screamer-VST3-macOS</b>, décompressez-le et copiez <b>Screamer.vst3</b> dans <b>~/Bibliothèque/Audio/Plug-Ins/VST3</b>. Si macOS le bloque, tapez <b>xattr -cr ~/Library/Audio/Plug-Ins/VST3/Screamer.vst3</b> dans le Terminal. Le binaire est universel (Apple Silicon et Intel)."),
       ("Reaper", "Options &gt; Préférences &gt; Plug-ins &gt; VST &gt; <b>Re-scan</b>. Le plugin apparaît sous le nom <b>Screamer (NINE HANDS | DSP)</b>. Pour le piloter avec des footswitchs et pédales d'expression MIDI, la piste doit recevoir le MIDI du contrôleur (armement ou monitoring d'entrée, entrée MIDI réglée sur votre appareil, par exemple la M-Vave Chocolate Plus).")],
 ov_t="3. Vue d'ensemble de l'interface",
 ov_rows=[["#", "Commande", "Rôle"],
   ["1", "DRIVE", "Quantité de saturation. Glisser vers le haut / le bas, molette, double-clic = midi, clic droit = MIDI Learn (valable pour toutes les commandes)."],
   ["2", "TONE", "Aigus : sombre à gauche, brillant à droite."],
   ["3", "LEVEL", "Volume de sortie."],
   ["4", "Écran", "Réglage de la commande que vous venez de bouger ; apparaît quand un réglage bouge."],
   ["5", "Barre de presets", "Flèches = preset usine précédent / suivant, clic sur le nom = menu des presets."],
   ["6", "LED", "Rouge = effet actif, éteinte = bypass."],
   ["7", "Footswitch", "Effet actif / bypass."],
   ["8", "OUT", "Jack de sortie."],
   ["9", "IN", "Jack d'entrée."]],
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
 learn=["<b>MIDI Learn</b> : clic droit sur une commande, choisissez <b>MIDI Learn: &lt;nom&gt; (CC n)</b> (<b>—</b> si rien n'est assigné), puis bougez la pédale d'expression ou appuyez sur le bouton MIDI. L'écran affiche <b>MIDI LEARN: move a control for Drive</b>, puis confirme pendant 2 secondes, par ex. <b>Drive = CC 64</b>. <b>Clear MIDI</b> retire une assignation ; clic droit &gt; MIDI &gt; <b>Clear all MIDI assignments</b> les retire toutes. Les assignations sont sauvegardées avec le projet.",
        "<b>Pédales d'expression</b> : les mouvements ne sont jamais saccadés. Screamer rejoint chaque nouvelle valeur par une rampe sur le temps mesuré entre deux messages ; la course réelle de votre pédale est apprise automatiquement (une pédale qui n'envoie que 2 à 116 atteint quand même exactement 0 et 100 %). Pour un potard sur un CC de 0 à 31, le CC n+32 est lu comme sa partie fine (14 bits).",
        "<b>Footswitch MIDI</b> : à accrochage (par défaut) ou momentané, clic droit &gt; Settings. <b>Program Change 1 à 10</b> : rappel des presets usine. Tous les paramètres sont aussi automatisables dans le DAW."],
 win_t="7. Fenêtre",
 win=["Screamer utilise le format pédale simple de NINE HANDS | DSP : la fenêtre montre la pédale seule, plein cadre (visuel de 1800 px de haut, largeur aux proportions de la pédale), elle s'ouvre à 60 % et ne peut jamais être réduite en dessous. Clic droit &gt; <b>Plugin size</b> : <b>60 %</b>, <b>75 %</b> ou <b>100 %</b>, « (default) » indiquant la taille par défaut ; <b>Default size (new windows)</b> choisit la taille d'ouverture de toutes les nouvelles fenêtres de Screamer (réglage commun à toutes les instances) et redimensionne aussitôt la fenêtre courante. Vous pouvez aussi tirer le coin en bas à droite jusqu'à 150 % (les proportions sont conservées).",
      "L'<b>écran</b> affiche le réglage du potard que vous venez de bouger (par ex. <i>DRIVE 64 %</i>) ; il apparaît quand un réglage bouge et s'efface au bout de 2,5 s. Il affiche aussi les messages du MIDI Learn. La <b>barre de presets</b> en dessous affiche en permanence le preset (ou <i>Edited</i>)."],
 bar_cap="Écran et barre de presets.",
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

W = A4[0] - 36 * mm
LOGO = os.path.join(ROOT, "assets", "nine_hands_logo_blanc.png")
def section(lang):
    t = T[lang]; f = []
    f.append(NextPageTemplate("p"))
    f.append(Spacer(1, 2 * mm)); f.append(P(t["lang"], "coverlang")); f.append(Spacer(1, 2 * mm))
    f.append(img(cover, W * 0.56)); f.append(Spacer(1, 1 * mm))
    f.append(P("S C R E A M E R", "cover")); f.append(P(t["sub"], "coversub"))
    f.append(Spacer(1, 2 * mm)); f.append(P(t["ver"], "coversub")); f.append(Spacer(1, 7 * mm))
    f.append(img(LOGO, 52 * mm))
    f.append(PageBreak())
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
    wt = Table([[[P(t["win"][1])], [img(bar_img, 66 * mm), P(t["bar_cap"], "small")]]], colWidths=[W - 70 * mm, 70 * mm])
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
                      title="SCREAMER - Manual / Notice v" + VERSION, author="NINE HANDS | DSP")
def cover_bg(c, doc):
    c.saveState(); c.setFillColor(colors.black); c.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
    c.setFillColor(ACC); c.rect(0, A4[1] - 3 * mm, A4[0], 3 * mm, stroke=0, fill=1); c.restoreState()
doc.addPageTemplates([PageTemplate(id="cover", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="fc")], onPage=cover_bg),
                      PageTemplate(id="p", frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")], onPage=deco)])
en = section("en"); fr = section("fr")
en[-1:] = [NextPageTemplate("cover"), PageBreak()]
doc.build(en + fr[:-1])
print(OUT)
