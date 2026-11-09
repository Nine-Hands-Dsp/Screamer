# Screamer (NINE HANDS | DSP) — VST3

Overdrive au format pédale simple (référence de format : Echoflex / Doorn / Strong Pickle), reproduction du circuit de
l'**Ibanez TS9 Tube Screamer**. Usage personnel. Windows 11 et macOS (binaire universel).
Visuel original NINE HANDS | DSP généré par `tools/make_art.py` : disposition des potards de la TS9 (DRIVE et LEVEL en haut,
TONE plus petit au milieu), boîtier rouge sang de bœuf imprimé d'un grand visage qui crie (`design/source/portrait.svg`, encre noire,
sous toutes les commandes et inscriptions, coupé aux bords du boîtier), pièces photo du kit maison ; il ne reprend pas l'habillage Ibanez.

<p align="center">
  <a href="https://github.com/Nine-Hands-Dsp/screamer/releases/latest/download/Screamer-VST3-Windows.zip"><img alt="Télécharger pour Windows" src="https://img.shields.io/badge/%E2%AC%87%20T%C3%A9l%C3%A9charger-Windows-0078D6?style=for-the-badge"></a>
  <a href="https://github.com/Nine-Hands-Dsp/screamer/releases/latest/download/Screamer-VST3-macOS.zip"><img alt="Télécharger pour macOS" src="https://img.shields.io/badge/%E2%AC%87%20T%C3%A9l%C3%A9charger-macOS-111111?style=for-the-badge&logo=apple&logoColor=white"></a>
  <br>
  <a href="https://github.com/Nine-Hands-Dsp/screamer/releases/latest"><img alt="Dernière version" src="https://img.shields.io/github/v/release/Nine-Hands-Dsp/screamer?label=derni%C3%A8re%20version&color=b0141c"></a>
</p>

## Installation via GitHub

1. Le push sur `main` lance la compilation (onglet **Actions**) : Windows (`windows-2022`) et macOS, puis publie la version en **Release** (`v<version>`) ; les boutons ci-dessus téléchargent toujours la dernière.
2. Télécharger le zip (boutons ci-dessus, ou artefact de l'onglet Actions) :
   - **Windows** : copier `Screamer.vst3` dans `C:\Program Files\Common Files\VST3\`
   - **macOS** : dézipper puis copier `Screamer.vst3` dans `~/Library/Audio/Plug-Ins/VST3/`
     (premier lancement : `xattr -cr ~/Library/Audio/Plug-Ins/VST3/Screamer.vst3` si macOS le bloque)
3. Relancer l'analyse des plugins. Le plugin apparaît comme **Screamer (NINE HANDS | DSP)**.

## La pédale d'origine et le plugin

| Élément | TS9 | Dans Screamer (`ScreamerDSP.h`) |
|---|---|---|
| Tampon d'entrée | Q1 2SC1815 suiveur, liaison 20 nF sur ≈ 446 k | Passe-haut ≈ 18 Hz, puis liaison 1 µF / 10 k (≈ 16 Hz) |
| Étage d'écrêtage | JRC4558 non inverseur ; vers la masse 4,7 k + 47 nF ; contre-réaction (51 k + DRIVE 500 k log) // 51 pF // 2 diodes 1S1588 tête-bêche | **Résolu à chaque échantillon** : intégration trapézoïdale des deux condensateurs + Newton sur l'équation de Shockley des diodes (Is 2,52 nA, n 1,752), sur-échantillonnage x4 (RIF Kaiser 128 points), sortie limitée en douceur par les rails du 4558 |
| Bosse de médiums | Seules les fréquences > 720 Hz sont amplifiées ; sortie = signal propre + tension des diodes | Vient du modèle, rien d'ajouté : gain des médiums ≈ 12 (DRIVE 0) à ≈ 118 (DRIVE 10), grave à gain 1 |
| TONE | 1 k / 220 nF (723 Hz) puis étage actif : pot 20 k entre les entrées + et −, 220 Ω + 220 nF au curseur, 10 k, 1 k | Fonction de transfert exacte du 2e ordre (analyse nodale), transformée bilinéaire pré-déformée à 1 kHz ; courbe du potard répartie pour un aigu régulier en dB (−18,6 → −2,5 dB à 4 kHz, mêmes extrêmes que la pédale) |
| LEVEL | Pot 100 k log en diviseur | Courbe log 15 % à mi-course ; DRIVE / TONE / LEVEL à midi ≈ niveau de la guitare (0,1 – 0,15 V crête), +15 dB en haut ; **pas de plafond à 0 dBFS** (v1.3) : seul plafond, l'excursion des amplis op en 9 V (±3,4 V ≈ +10,6 dBFS), comme la pédale devant un ampli |
| Sortie TS9 | 470 Ω / 100 k (TS808 : 100 Ω / 10 k) | Sans effet audible sur une entrée haute impédance : liaison seule |
| Bypass | Bufferisé (JFET) | Signal sec aligné sur la latence (32 échantillons, annoncée au DAW), fondu de 3 ms |
| Noise gate (ajout) | — | Clic droit > *Noise gate* : Off (défaut) / Light / Medium / Strong |

Mesures (`tests/test_dsp.cpp`, `tests/bench.cpp`) : réponse petits signaux, THD, niveau par position, ≈ 6 % d'un cœur en stéréo à 48 kHz (-O2).

Sources : analyse Electrosmash (Tube Screamer), Geofex (*The Technology of the Tube Screamer*), D. Yeh, *Simplified,
physically-informed models of distortion and overdrive guitar effects pedals* (DAFx 2007) pour l'étage de tonalité,
forums Seymour Duncan / PedalPCB pour les différences TS9 / TS808 (sortie 470 Ω / 100 k, diodes 1S1588).

## Interface

- **Visuel 1235 × 1800 px** (`background.png`) : la pédale plein cadre, fond transparent seulement autour des jacks (règle des pédales simples NINE HANDS | DSP) ; la fenêtre montre la pédale seule.
- **Sérigraphie vectorielle** : noms des potards, SCREAMER / OVERDRIVE, IN / OUT, graduations et logo NINE HANDS | DSP (`NineHandsLogo.svg`) sont dessinés par le plugin (Poppins), nets à toutes les tailles et sur les écrans haute densité ; le fond est mis en cache à la résolution physique de l'écran.
- Fenêtre ouverte à **493 px de haut** (338 × 493), impossible de la réduire en dessous, proportions bloquées, jusqu'à 150 %. Clic droit > *Plugin size* : 60 % / 75 % / 100 % ; *Default size (new windows)* pour la taille des nouvelles fenêtres.
- **Écran d'état** (réglage en %, messages MIDI Learn) et **barre de presets** (flèches, menu) dessinés par le plugin, police Poppins.
- Potards agrandis (v1.3.2) : photo du kit (`assets/kit/knob_photo.png`), seul le repère crème tourne ; double-clic = midi.
- Footswitch du kit (référence Echoflex) : bascule à l'appui, bouton assombri tant qu'on appuie, reflet rouge de la LED sur l'écrou.
- LED rouge (photo du kit, couleur d'origine), façade éclairée par un calque précalculé, fondu 0,45 / 0,28.
- Jacks photo du kit affleurant les tranches (OUT à gauche, IN à droite), inscriptions IN / OUT à leur hauteur ; occlusion sur la coque autour des jacks, des potards, de la LED et du footswitch.
- **Anti-gel v2** : rendu logiciel forcé sous Windows, fenêtre opaque, timer 30 Hz qui ne redessine que ce qui change, caches reconstruits par le timer, chien de garde 1,5 s, jamais de `setSize` dans `resized()` ; côté audio, file vidée sur le thread de messages, paramètres lus par pointeurs. JUCE 8.0.15.

## MIDI

**Aucun CC assigné par défaut** : clic droit sur une commande > *MIDI Learn* (Drive, Tone, Level, Footswitch).
CC n+32 = poids faible 14 bits pour un potard sur CC 0-31. Pédales d'expression : rampe sur l'intervalle entre deux CC,
course apprise (2-116 → 0-100 %). Footswitch MIDI à accrochage ou momentané. Program Change 1-10 = presets d'usine.

## Presets d'usine

Classic TS9 · Texas Blues · Metal Boost (7 strings) · Edge of Breakup · Rhythm Crunch · Singing Lead · Warm & Round ·
Bright Humbucker · Full Drive · Clean Mid Boost.

## Fichiers

- `ScreamerDSP.h` : moteur audio sans JUCE ; `PluginProcessor.*`, `PluginEditor.*` ; `Layout.h` généré.
- `tools/make_art.py` (+ `tools/photo_controls.py`) : visuel, calques, `Layout.h`.
- `tools/render` : compile la vraie fenêtre sous Linux et exporte les captures (`design/renders`).
- `tools/manual.py` : notice bilingue `docs/Screamer_Manual_EN-FR_v1.3.2.pdf` (repères lus dans `tools/layout.json`).
- `tests/verify.cpp` : vérification du moteur contre les valeurs publiées (gain de l'étage d'écrêtage modèle / formule, repliement, bypass, fréquences d'échantillonnage, signaux extrêmes).

## Versions

- **1.3.2** (9 nov. 2026) : visuel 1235 × 1800 ; potards agrandis ; textes, graduations (toutes de même taille) et nouveau logo NINE HANDS | DSP dessinés en vectoriel ; fond net sur écrans haute densité ; traits du visage lissés ; jacks affleurant le boîtier ; occlusion autour des éléments en relief.
- **1.3.1** (8 nov. 2026) : notice : conseils d'utilisation avec Ampire et Impulse (Two Notes Genome n'est plus utilisé).
- **1.3.0** (8 nov. 2026) : le plafond de sécurité à 0 dBFS est retiré : il écrasait le réglage metal (DRIVE 0, LEVEL à fond) dès 0,2 V de guitare ; seul reste l'excursion réelle des amplis op (±3,4 V). Preset 3 « Metal Boost (7 strings) » : DRIVE 0, TONE 13 h, LEVEL à fond. Image 1016 × 1800 aux proportions d'origine de la pédale (1800 px de haut, largeur homogène). Composants vérifiés avec les TS9 d'origine (JRC4558 / TA75558, diodes 1S1588, sortie 470 Ω / 100 k).
- **1.2.0** (8 nov. 2026) : visuel 965 × 1800 px, pédale plein cadre, transparent seulement autour des jacks ; la fenêtre ne montre plus que la pédale (mêmes hauteurs : 493 / 719 / 958 px, jusqu'à 1437).
- **1.1.0** (8 nov. 2026) : disposition des potards de la TS9, jacks, écran, presets et LED descendus, titre au milieu ; grand visage imprimé sur la coque ; moteur vérifié (gain 11,9 → 118, conforme à Electrosmash ; 1 kHz à ±0,05 dB de la formule à DRIVE 0) ; coefficients recalculés seulement quand un potard bouge.
- **1.0.0** (8 nov. 2026) : première version.
