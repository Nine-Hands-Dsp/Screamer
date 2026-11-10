#include "PluginEditor.h"
#include "BinaryData.h"
#include "Layout.h"
#include "WigaWindowSize.h"

using namespace juce;

namespace
{
    // repere 760 x 958 (fond 2x), positions generees par tools/make_art.py dans Layout.h
    const Rectangle<float> presetRect = layout::presetRect;

    const float rotStart = MathConstants<float>::pi * (7.0f / 6.0f);    // -150 degres (7 h)
    const float rotEnd   = MathConstants<float>::pi * (17.0f / 6.0f);   // +150 degres (5 h)

    const Colour inkCream (0xffece2cc);     // serigraphie creme du visuel
    const Colour accent (0xffff4a36);       // rouge de la LED
    const Colour panel (0xff160607);        // fond de l'ecran et de la barre (rouge tres sombre)

    const char* const valueIds[] = { "drive", "tone", "level", "active", "gate" };
    constexpr int numValueIds = 5;
}

//==============================================================================
// POTARDS : repere creme arrondi (de 0,42 a 0,90 du rayon), lumiere fixe en haut a gauche
//==============================================================================
bool ScreamerKnob::hitTest (int x, int y)
{
    const auto c = getLocalBounds().toFloat().getCentre();
    return c.getDistanceFrom ({ (float) x, (float) y }) <= getWidth() * 0.5f;
}

void ScreamerKnobLookAndFeel::drawRotarySlider (Graphics& g, int x, int y, int w, int h,
                                                float pos, float startAngle, float endAngle, Slider&)
{
    const auto c = Rectangle<float> ((float) x, (float) y, (float) w, (float) h).getCentre();
    const float R = (float) jmin (w, h) * 0.5f;
    const float a = startAngle + pos * (endAngle - startAngle);
    const Point<float> dir (std::sin (a), -std::cos (a));
    const Point<float> p0 = c + dir * (0.42f * R), p1 = c + dir * (0.90f * R);
    const float lw = jmax (1.4f, 0.062f * R);
    Path line; line.startNewSubPath (p0); line.lineTo (p1);
    // ombre tres fine (le repere est peint, a peine en relief), lumiere en haut a gauche
    g.setColour (Colours::black.withAlpha (0.45f));
    g.strokePath (line, PathStrokeType (lw * 1.15f, PathStrokeType::curved, PathStrokeType::rounded),
                  AffineTransform::translation (R * 0.010f, R * 0.014f));
    const float lightFacing = 0.5f + 0.5f * std::cos (a + MathConstants<float>::pi * 0.25f);
    g.setColour (inkCream.withMultipliedBrightness (0.94f + 0.06f * lightFacing));
    g.strokePath (line, PathStrokeType (lw, PathStrokeType::curved, PathStrokeType::rounded));
}

//==============================================================================
// FOOTSWITCH (fonctionnement d'Echoflex)
//==============================================================================
FootSwitchArea::FootSwitchArea (RangedAudioParameter& p)
    : attachment (p, [this] (float v) { value = v > 0.5f; repaint(); })
{
    attachment.sendInitialUpdate();
    setMouseCursor (MouseCursor::PointingHandCursor);
}

bool FootSwitchArea::hitTest (int x, int y)
{
    // zone d'appui circulaire : le bouton et l'ecrou (le sprite contient aussi l'ombre)
    const auto c = getLocalBounds().toFloat().getCentre();
    return c.getDistanceFrom ({ (float) x, (float) y }) <= (float) getWidth() * (layout::footR * 1.35f / layout::fsS);
}

void FootSwitchArea::paint (Graphics& g)
{
    const auto b = getLocalBounds().toFloat();
    if (ledLevel > 0.003f && reflection.isValid())
    {
        g.setOpacity (ledLevel);
        g.drawImage (reflection, b);
        g.setOpacity (1.0f);
    }
    if (pressed)
    {
        // bouton assombri tant qu'on appuie (disque noir a 25 %)
        const float r = b.getWidth() * (layout::footR / layout::fsS) * 0.98f;
        const auto c = b.getCentre();
        g.setColour (Colours::black.withAlpha (0.25f));
        g.fillEllipse (c.x - r, c.y - r, r * 2.0f, r * 2.0f);
    }
}

void FootSwitchArea::mouseDown (const MouseEvent& e)
{
    if (e.mods.isPopupMenu()) { if (onRightClick) onRightClick(); return; }
    pressed = true;
    repaint();
    attachment.setValueAsCompleteGesture (value ? 0.0f : 1.0f);    // bascule des l'appui
    if (onUserChange) onUserChange();
}

void FootSwitchArea::mouseUp (const MouseEvent& e)
{
    if (e.mods.isPopupMenu()) return;
    pressed = false;
    repaint();
}

//==============================================================================
// EDITEUR
//==============================================================================
ScreamerAudioProcessorEditor::ScreamerAudioProcessorEditor (ScreamerAudioProcessor& p)
    : AudioProcessorEditor (&p), proc (p),
      footswitch (*p.apvts.getParameter ("active"))
{
    background = ImageCache::getFromMemory (BinaryData::background_png, BinaryData::background_pngSize);
    glow       = ImageCache::getFromMemory (BinaryData::glow_red_png, BinaryData::glow_red_pngSize);
    ledOn      = ImageCache::getFromMemory (BinaryData::led_on_png, BinaryData::led_on_pngSize);
    footswitch.reflection = ImageCache::getFromMemory (BinaryData::fs_refl_png, BinaryData::fs_refl_pngSize);
    labelFace = Typeface::createSystemTypefaceFor (BinaryData::PoppinsMedium_ttf, BinaryData::PoppinsMedium_ttfSize);
    boldFace  = Typeface::createSystemTypefaceFor (BinaryData::PoppinsBold_ttf, BinaryData::PoppinsBold_ttfSize);
    lightFace = Typeface::createSystemTypefaceFor (BinaryData::PoppinsLight_ttf, BinaryData::PoppinsLight_ttfSize);
    if (auto xml = XmlDocument::parse (String::fromUTF8 (BinaryData::NineHandsLogo_svg, BinaryData::NineHandsLogo_svgSize)))
        logo = Drawable::createFromSVG (*xml);
    buildPrint();
    menuLnf.reg = lightFace; menuLnf.med = labelFace; menuLnf.bold = boldFace;
    setLookAndFeel (&menuLnf);             // menus (et sous-menus) au design d'Octopus

    // index des commandes = learnDef du processeur (0-2 potards, 3 footswitch)
    rightClickFwd.callback = [this] (Component* c)
    {
        int idx = -1;
        for (int i = 0; i < ScreamerAudioProcessor::numKnobs; ++i)
            if (c == &knobs[i]) idx = i;
        showContextMenu (idx);
    };

    for (int i = 0; i < ScreamerAudioProcessor::numKnobs; ++i)
    {
        auto& s = knobs[i];
        s.setSliderStyle (Slider::RotaryHorizontalVerticalDrag);
        s.setTextBoxStyle (Slider::NoTextBox, false, 0, 0);
        s.setRotaryParameters (rotStart, rotEnd, true);
        s.setMouseDragSensitivity (220);
        s.setDoubleClickReturnValue (true, 5.0);
        s.setLookAndFeel (&lnf);
        s.setMouseCursor (MouseCursor::PointingHandCursor);
        s.addMouseListener (&rightClickFwd, false);
        s.onDragStart = [this] { proc.currentPreset = -1; };
        addAndMakeVisible (s);
        knobAtt[i] = std::make_unique<AudioProcessorValueTreeState::SliderAttachment> (proc.apvts, ScreamerAudioProcessor::knobId (i), s);
    }

    footswitch.onRightClick = [this] { showContextMenu (3); };
    footswitch.onUserChange = [this] { proc.currentPreset = -1; };
    addAndMakeVisible (footswitch);

    for (int i = 0; i < numValueIds; ++i) lastValues[i] = proc.raw (valueIds[i]);
    lastPresetCounter = proc.presetCounter.load();
    lastMidiCount = proc.midiCounter.load();
    ledLevel = proc.rawAt (ScreamerAudioProcessor::rActive) > 0.5f ? 1.0f : 0.0f;

    // Taille par defaut = taille minimale (impossible de reduire en dessous), proportions bloquees
    const int defaultW = roundToInt ((float) defaultH * baseW / baseH);
    setResizable (true, true);
    setResizeLimits (defaultW, defaultH, roundToInt ((float) maxH * baseW / baseH), maxH);
    if (auto* cons = getConstrainer())
        cons->setFixedAspectRatio ((double) baseW / (double) baseH);
    setOpaque (true);                      // anti-gel : l'hote ne redessine jamais ce qui est derriere la fenetre
    setSize (defaultW, defaultH);
    // taille des nouvelles fenetres : celle choisie dans le menu « Default size (new windows) »
    setScaledHeight (sizeHeight (WigaWindowSize::defaultIndex (JucePlugin_Name, numSizes)));
    rebuildCaches();
    startTimerHz (30);
}

ScreamerAudioProcessorEditor::~ScreamerAudioProcessorEditor()
{
    stopTimer();
    for (auto& s : knobs) { s.removeMouseListener (&rightClickFwd); s.setLookAndFeel (nullptr); }
    setLookAndFeel (nullptr);
}

//==============================================================================
int ScreamerAudioProcessorEditor::sizeHeight (int idx)
{
    const int h[numSizes] = { (int) defaultH, roundToInt (refH * 0.75f), (int) refH };
    return h[jlimit (0, numSizes - 1, idx)];
}

void ScreamerAudioProcessorEditor::setScaledHeight (int h)
{
    h = jlimit ((int) defaultH, (int) maxH, h);
    setSize (roundToInt ((float) h * baseW / baseH), h);
}

Rectangle<int> ScreamerAudioProcessorEditor::scaled (Rectangle<float> r) const
{
    const float s = (float) getHeight() / baseH;
    return r.transformedBy (AffineTransform::scale (s)).getSmallestIntegerContainer();
}

float ScreamerAudioProcessorEditor::physicalScale() const
{
    if (forcedScale > 0.0f) return forcedScale;
    return jlimit (1.0f, 4.0f, (float) Component::getApproximateScaleFactorForComponent (this));
}

void ScreamerAudioProcessorEditor::showStatus() { statusUntil = Time::getMillisecondCounterHiRes() + 2500.0; }

//==============================================================================
// Caches d'affichage : fond et calque lumineux a la taille de la fenetre (reconstruits par le timer seulement)
//==============================================================================
void ScreamerAudioProcessorEditor::rebuildCaches (float sc)
{
    if (sc <= 0.0f) sc = cacheScale > 0.0f ? cacheScale : physicalScale();
    const int w = getWidth(), h = getHeight();
    if (w <= 0 || h <= 0) return;
    if (w == cacheW && h == cacheH && std::abs (sc - cacheScale) < 0.01f && bgScaled.isValid()) return;
    cacheW = w; cacheH = h; cacheScale = sc;
    const int pw = roundToInt ((float) w * sc), ph = roundToInt ((float) h * sc);
    bgScaled = (pw >= background.getWidth()) ? background : background.rescaled (pw, ph, Graphics::highResamplingQuality);
    const float s = (float) h / baseH;
    const int gpx = roundToInt (layout::glowRect.getWidth() * s * sc);
    glowS = (gpx >= glow.getWidth()) ? glow : glow.rescaled (gpx, gpx, Graphics::highResamplingQuality);
    repaint();
}

void ScreamerAudioProcessorEditor::resized()
{
    // anti-gel : jamais de setSize ici ; les limites du constrainer suffisent
    for (int i = 0; i < ScreamerAudioProcessor::numKnobs; ++i)
    {
        const auto c = layout::knobPos[i]; const float r = layout::knobR[i];
        knobs[i].setBounds (scaled ({ c.x - r, c.y - r, r * 2.0f, r * 2.0f }));
    }
    const float fr = layout::fsS * 0.5f;
    footswitch.setBounds (scaled ({ layout::fsPos.x - fr, layout::fsPos.y - fr, fr * 2.0f, fr * 2.0f }));
    resizeSettle = 4;
}

//==============================================================================
// Anti-gel v2 (NINE HANDS | DSP) :
//  1. moteur de rendu logiciel force sur Windows, applique a chaque nouvelle fenetre hote (peer)
//     et reverifie toutes les secondes, jamais en boucle ;
//  2. aucun calcul lourd dans paint() : caches reconstruits par le timer seulement ;
//  3. chien de garde : redessin demande non servi en 1,5 s -> moteur de rendu reapplique, tout redessine ;
//  4. cote audio : aucun appel a l'hote ni allocation depuis le thread audio (voir PluginProcessor).
//==============================================================================
void ScreamerAudioProcessorEditor::useSoftwareRenderer()
{
    auto* peer = getPeer();
    if (peer != lastPeer) { lastPeer = peer; repaint(); }
   #if JUCE_WINDOWS
    if (peer != nullptr)
    {
        int sw = peer->getAvailableRenderingEngines().indexOf ("Software Renderer");
        if (sw < 0) sw = 0;
        if (peer->getCurrentRenderingEngine() != sw) peer->setCurrentRenderingEngine (sw);
    }
   #endif
}

void ScreamerAudioProcessorEditor::parentHierarchyChanged() { useSoftwareRenderer(); }
void ScreamerAudioProcessorEditor::visibilityChanged()      { useSoftwareRenderer(); if (isShowing()) repaint(); }

void ScreamerAudioProcessorEditor::askRepaint (Rectangle<int> r)
{
    if (repaintAskedMs <= 0.0) repaintAskedMs = Time::getMillisecondCounterHiRes();
    repaint (r);
}

//==============================================================================
String ScreamerAudioProcessorEditor::buildStatusLine() const
{
    const int i = lastChanged;
    if (i < 0) return {};
    const String id = valueIds[i];
    const float v = proc.raw (valueIds[i]);
    if (i < 3)          return id + "  " + String (roundToInt (v * 10.0f)) + " %";
    if (id == "gate")   return "noise gate " + ScreamerAudioProcessor::gateNames()[jlimit (0, 3, roundToInt (v))].toLowerCase();
    return v > 0.5f ? "effect on" : "bypass";
}

String ScreamerAudioProcessorEditor::buildPresetLine() const
{
    const int cp = proc.currentPreset.load();
    String s;
    if (cp >= 0 && cp < ScreamerAudioProcessor::getNumFactoryPresets())
        s << "P" << (cp + 1) << "  " << ScreamerAudioProcessor::getFactoryPreset (cp).name;
    else if (cp > 100) s << "User " << (cp - 100);
    else               s << "Edited";
    return s;
}

//==============================================================================
void ScreamerAudioProcessorEditor::timerCallback()
{
    const double now = Time::getMillisecondCounterHiRes();
    if (getPeer() != lastPeer || now - lastRendererCheckMs > 1000.0) { lastRendererCheckMs = now; useSoftwareRenderer(); }

    if (resizeSettle > 0 && --resizeSettle == 0) rebuildCaches();
    else if (resizeSettle == 0 && now - lastScaleCheckMs > 250.0)
    {
        lastScaleCheckMs = now;
        const float sc = physicalScale();
        if (std::abs (sc - cacheScale) > 0.01f) rebuildCaches (sc);
    }

    if (repaintAskedMs > 0.0 && isShowing() && now - repaintAskedMs > 1500.0 && lastPaintMs < repaintAskedMs)
    {
        repaintAskedMs = 0.0; lastPeer = nullptr;
        useSoftwareRenderer(); repaint();
    }

    int changed = -1, numChanged = 0;
    for (int i = 0; i < numValueIds; ++i)
    {
        const float v = proc.raw (valueIds[i]);
        if (std::abs (v - lastValues[i]) > 1.0e-4f) { lastValues[i] = v; changed = i; ++numChanged; }
    }
    const int pcount = proc.presetCounter.load();
    if (pcount != lastPresetCounter) { lastPresetCounter = pcount; numChanged = 0; }
    if (numChanged == 1) { lastChanged = changed; showStatus(); learnLineUntil = 0.0; }
    for (int i = 0; i < ScreamerAudioProcessor::numKnobs; ++i)
        if (knobs[i].isMouseButtonDown()) { lastChanged = i; showStatus(); learnLineUntil = 0.0; }

    // MIDI Learn : attente puis confirmation 2 s dans la ligne d'etat
    const int lt = proc.learnTarget.load();
    const int learned = proc.lastLearned.exchange (-1);
    if (learned >= 0)
    {
        learnLine = String (ScreamerAudioProcessor::learnDef (learned).name) + " = CC " + String (proc.ccMap[learned].load());
        learnLineUntil = now + 2000.0;
        statusUntil = jmax (statusUntil, learnLineUntil);
    }
    else if (lt >= 0)
    {
        learnLine = "MIDI LEARN: move a control for " + String (ScreamerAudioProcessor::learnDef (lt).name);
        learnLineUntil = now + 200.0;
        statusUntil = jmax (statusUntil, now + 200.0);
    }
    const int mc = proc.midiCounter.load();
    if (mc != lastMidiCount) { lastMidiCount = mc; midiFlash = 8; }
    if (midiFlash > 0) --midiFlash;

    const float target = now < statusUntil ? 1.0f : 0.0f;
    statusAlpha += (target - statusAlpha) * (target > statusAlpha ? 0.45f : 0.25f);   // ~120 ms a l'apparition, ~300 ms au retour
    if (statusAlpha < 0.005f) statusAlpha = 0.0f;
    if (statusAlpha > 0.995f) statusAlpha = 1.0f;

    // LED rouge = effet actif ; fondu 0,45 a l'allumage / 0,28 a l'extinction
    const bool on = proc.rawAt (ScreamerAudioProcessor::rActive) > 0.5f;
    ledLevel += ((on ? 1.0f : 0.0f) - ledLevel) * (on ? 0.45f : 0.28f);
    if (ledLevel < 0.003f) ledLevel = 0.0f;
    if (ledLevel > 0.997f) ledLevel = 1.0f;
    if (std::abs (ledLevel - drawnLed) > 0.004f)
    {
        drawnLed = ledLevel;
        footswitch.ledLevel = ledLevel;
        askRepaint (scaled (layout::glowRect));
        footswitch.repaint();
    }

    const auto l1 = (learnLineUntil > 0.0 && now < learnLineUntil + 800.0 ? learnLine : buildStatusLine()), pl = buildPresetLine();
    const bool textChanged = l1 != lastLine1;
    lastLine1 = l1;
    if (std::abs (statusAlpha - drawnStatus) > 0.003f || (statusAlpha > 0.0f && textChanged))
    {
        drawnStatus = statusAlpha;
        askRepaint (scaled (presetRect.expanded (3.0f)));
    }
    if (pl != lastPreset || hoverZone != drawnHover || midiFlash > 0)
    {
        lastPreset = pl; drawnHover = hoverZone;
        askRepaint (scaled (presetRect.expanded (3.0f)));
    }
}

//==============================================================================
void ScreamerAudioProcessorEditor::drawLed (Graphics& g)
{
    const float level = ledLevel;
    if (level <= 0.003f) return;
    // la facade recoit la lumiere de la LED (calque alpha precalcule : seule la lumiere ajoutee)
    if (glowS.isValid()) { g.setOpacity (level); g.drawImage (glowS, layout::glowRect); }
    // lentille allumee (photo de LED rouge du kit)
    const auto c = layout::ledPos;
    const float hs = layout::ledS * 0.5f;
    if (ledOn.isValid()) { g.setOpacity (level); g.drawImage (ledOn, { c.x - hs, c.y - hs, hs * 2.0f, hs * 2.0f }); }
    g.setOpacity (1.0f);
    // tres leger halo optique autour de la lentille
    const float hr = 20.0f;
    ColourGradient halo (accent.withAlpha (0.30f * level), c.x, c.y, accent.withAlpha (0.0f), c.x + hr, c.y, true);
    halo.addColour (0.4, accent.withAlpha (0.08f * level));
    g.setGradientFill (halo);
    g.fillEllipse (c.x - hr, c.y - hr, hr * 2.0f, hr * 2.0f);
}


// Pastille unique (regle NINE HANDS | DSP) : barre de presets au repos ; des qu'un reglage bouge, la ligne d'etat
// prend sa place en fondu croise (meme pastille, meme police, aucun saut), puis s'efface ~2,5 s apres le dernier mouvement.
void ScreamerAudioProcessorEditor::drawPresetBar (Graphics& g)
{
    const auto r = presetRect;
    const float a = statusAlpha, pa = 1.0f - a;
    g.setColour (panel.withAlpha (0.80f));
    g.fillRoundedRectangle (r, r.getHeight() * 0.5f);
    g.setColour (inkCream.withAlpha ((hoverZone != 0 ? 0.55f : 0.28f) * pa + 0.40f * a));
    g.drawRoundedRectangle (r.reduced (0.6f), r.getHeight() * 0.5f, 1.2f);
    const Font f (FontOptions (labelFace).withHeight (layout::presetFont));
    const float aw = 34.0f;
    if (pa > 0.0f)
    {
        auto arrow = [&] (Rectangle<float> ar, bool left, bool hot)
        {
            Path p; const auto c = ar.getCentre(); const float sz = 6.0f;
            if (left) p.addTriangle (c.x + sz * 0.6f, c.y - sz, c.x + sz * 0.6f, c.y + sz, c.x - sz * 0.8f, c.y);
            else      p.addTriangle (c.x - sz * 0.6f, c.y - sz, c.x - sz * 0.6f, c.y + sz, c.x + sz * 0.8f, c.y);
            g.setColour (inkCream.withAlpha ((hot ? 1.0f : 0.6f) * pa));
            g.fillPath (p);
        };
        arrow (r.withWidth (aw), true, hoverZone == 1);
        arrow (r.withTrimmedLeft (r.getWidth() - aw), false, hoverZone == 3);
        g.setFont (f);
        g.setColour ((midiFlash > 0 ? Colour (0xffff8a70) : inkCream).withAlpha ((hoverZone == 2 ? 1.0f : 0.9f) * pa));
        g.drawFittedText (lastPreset, r.reduced (aw, 0.0f).toNearestInt(), Justification::centred, 1, 0.7f);
    }
    if (a > 0.0f)
    {
        g.setFont (f);
        g.setColour ((midiFlash > 0 ? Colour (0xffff8a70) : inkCream).withAlpha (a));
        g.drawFittedText (lastLine1.toUpperCase(), r.reduced (18.0f, 0.0f).toNearestInt(), Justification::centred, 1, 0.6f);
    }
}

//==============================================================================
// Serigraphie vectorielle : construite une fois en chemins (unites du plugin), remplie a l'echelle de la fenetre
//==============================================================================
void ScreamerAudioProcessorEditor::buildPrint()
{
    printPath.clear();
    for (const auto& t : layout::texts)
    {
        const Typeface::Ptr face = t.font == 1 ? boldFace : (t.font == 2 ? lightFace : labelFace);
        const Font font (FontOptions (face).withPointHeight (t.em));
        const String s (t.s);
        float total = 0.0f;
        for (int i = 0; i < s.length(); ++i)
            total += GlyphArrangement::getStringWidth (font, String::charToString (s[i])) + (i > 0 ? t.track : 0.0f);
        const float base = (font.getAscent() - font.getDescent()) * 0.5f;     // centre vertical entre ascendante et descendante
        GlyphArrangement ga;
        float x = -total * 0.5f;
        for (int i = 0; i < s.length(); ++i)
        {
            const String ch = String::charToString (s[i]);
            ga.addLineOfText (font, ch, x, base);
            x += GlyphArrangement::getStringWidth (font, ch) + t.track;
        }
        Path p; ga.createPath (p);
        p.applyTransform (AffineTransform::rotation (-t.rot * MathConstants<float>::pi / 180.0f).translated (t.x, t.y));
        printPath.addPath (p);
    }
    for (const auto& d : layout::dots)  printPath.addEllipse (d.x - d.r, d.y - d.r, d.r * 2.0f, d.r * 2.0f);
    for (const auto& r : layout::rules) printPath.addRectangle (r);
}

void ScreamerAudioProcessorEditor::drawPrint (Graphics& g)
{
    g.setColour (inkCream);
    g.fillPath (printPath);
    if (logo != nullptr)
    {
        const auto vb = logo->getDrawableBounds();
        const float w = layout::logoW, h = w * vb.getHeight() / jmax (1.0f, vb.getWidth());
        logo->drawWithin (g, { layout::logoPos.x - w * 0.5f, layout::logoPos.y - h * 0.5f, w, h }, RectanglePlacement::centred, 0.92f);
    }
}

void ScreamerAudioProcessorEditor::paint (Graphics& g)
{
    lastPaintMs = Time::getMillisecondCounterHiRes();
    repaintAskedMs = 0.0;
    g.fillAll (Colour (0xff111112));          // autour des jacks : le fond de l'image est transparent
    // anti-gel : aucun rescale ici, on dessine le cache existant (ou l'original en attendant le timer)
    const Image& bg = bgScaled.isValid() ? bgScaled : background;
    g.setImageResamplingQuality (&bg == &background ? Graphics::highResamplingQuality : Graphics::lowResamplingQuality);
    if (bg.isValid()) g.drawImage (bg, getLocalBounds().toFloat());

    const float s = (float) getHeight() / baseH;
    g.addTransform (AffineTransform::scale (s));
    g.setImageResamplingQuality (Graphics::mediumResamplingQuality);
    drawPrint (g);
    drawLed (g);
    drawPresetBar (g);
}

//==============================================================================
// Souris : barre de presets (fleches = precedent / suivant, nom = menu deroulant), clic droit = menu
//==============================================================================
static int presetZoneAt (Point<float> p)
{
    if (! presetRect.contains (p)) return 0;
    if (p.x < presetRect.getX() + 34.0f) return 1;
    if (p.x > presetRect.getRight() - 34.0f) return 3;
    return 2;
}

void ScreamerAudioProcessorEditor::mouseMove (const MouseEvent& e)
{
    const float s = (float) getHeight() / baseH;
    hoverZone = presetZoneAt (e.position / s);
    setMouseCursor (hoverZone != 0 ? MouseCursor::PointingHandCursor : MouseCursor::NormalCursor);
}

void ScreamerAudioProcessorEditor::mouseExit (const MouseEvent&) { hoverZone = 0; }

void ScreamerAudioProcessorEditor::mouseDown (const MouseEvent& e)
{
    if (e.mods.isPopupMenu()) { showContextMenu(); return; }
    const float s = (float) getHeight() / baseH;
    if (presetRect.contains (e.position / s) && statusAlpha > 0.0f)
        { statusUntil = 0.0; learnLineUntil = 0.0; }        // la ligne d'etat ne bloque pas : la barre de presets revient
    switch (presetZoneAt (e.position / s))
    {
        case 1: stepPreset (-1); break;
        case 2: showPresetMenu(); break;
        case 3: stepPreset (1); break;
        default: break;
    }
}

void ScreamerAudioProcessorEditor::stepPreset (int delta)
{
    const int n = ScreamerAudioProcessor::getNumFactoryPresets();
    int cp = proc.currentPreset.load();
    if (cp < 0 || cp >= n) cp = delta > 0 ? -1 : 0;
    proc.applyFactoryPreset ((cp + delta + n) % n);
}

void ScreamerAudioProcessorEditor::showPresetMenu()
{
    PopupMenu m;
    m.addSectionHeader ("Factory presets");
    for (int i = 0; i < ScreamerAudioProcessor::getNumFactoryPresets(); ++i)
        m.addItem (100 + i, String (i + 1) + ". " + ScreamerAudioProcessor::getFactoryPreset (i).name, true, proc.currentPreset.load() == i);
    m.addSeparator();
    PopupMenu load, save;
    for (int slot = 1; slot <= 9; ++slot)
    {
        const bool exists = proc.hasUserPreset (slot);
        load.addItem (200 + slot, "User " + String (slot) + (exists ? "" : "  (empty)"), exists, proc.currentPreset.load() == 100 + slot);
        save.addItem (300 + slot, "User " + String (slot) + (exists ? "  (overwrite)" : ""));
    }
    m.addSubMenu ("Load user preset", load);
    m.addSubMenu ("Save user preset", save);

    m.setLookAndFeel (&menuLnf);
    m.showMenuAsync (PopupMenu::Options().withTargetScreenArea (localAreaToGlobal (scaled (presetRect))),
        [safe = Component::SafePointer<ScreamerAudioProcessorEditor> (this)] (int r)
        {
            if (safe == nullptr || r == 0) return;
            auto& pr = safe->proc;
            if      (r >= 100 && r < 200) pr.applyFactoryPreset (r - 100);
            else if (r > 200 && r < 300)  pr.loadUserPreset (r - 200);
            else if (r > 300 && r < 400)  pr.saveUserPreset (r - 300);
            safe->showStatus();
        });
}

void ScreamerAudioProcessorEditor::handleMidiMenu (int r)
{
    if (r >= 1000 && r < 1000 + ScreamerAudioProcessor::numLearn)      proc.learnTarget.store (r - 1000);
    else if (r >= 1100 && r < 1100 + ScreamerAudioProcessor::numLearn) proc.ccMap[r - 1100].store (-1);
    else if (r == 1200) proc.learnTarget.store (-1);
    else if (r == 1201) { proc.learnTarget.store (-1); proc.resetMidiMap(); }
}

void ScreamerAudioProcessorEditor::showContextMenu (int learnIdx)
{
    PopupMenu menu;
    auto ccText = [this] (int i)
    {
        const int cc = proc.ccMap[i].load();
        return cc >= 0 ? "CC " + String (cc) : String (CharPointer_UTF8 ("\xe2\x80\x94"));
    };
    const int lt = proc.learnTarget.load();
    if (learnIdx >= 0)
    {
        const String name = ScreamerAudioProcessor::learnDef (learnIdx).name;
        menu.addItem (1000 + learnIdx, "MIDI Learn: " + name + " (" + ccText (learnIdx) + ")", true, lt == learnIdx);
        menu.addItem (1100 + learnIdx, "Clear MIDI: " + name, proc.ccMap[learnIdx].load() >= 0);
        if (lt >= 0) menu.addItem (1200, "Cancel MIDI learn");
        menu.addSeparator();
    }

    PopupMenu sizes;
    {
        // Plugin size : taille de cette fenetre + taille par defaut des nouvelles fenetres
        const char* names[numSizes] = { "60 %", "75 %", "100 %" };
        const int def = WigaWindowSize::defaultIndex (JucePlugin_Name, numSizes);
        PopupMenu defSizes;
        for (int i = 0; i < numSizes; ++i)
        {
            sizes.addItem (1 + i, String (names[i]) + (i == def ? "  (default)" : ""), true, std::abs (getHeight() - sizeHeight (i)) <= 2);
            defSizes.addItem (20 + i, names[i], true, i == def);
        }
        sizes.addSeparator();
        sizes.addSubMenu ("Default size (new windows)", defSizes);
        menu.addSubMenu ("Plugin size", sizes);
    }
    menu.addSeparator();

    PopupMenu factory;
    for (int i = 0; i < ScreamerAudioProcessor::getNumFactoryPresets(); ++i)
        factory.addItem (100 + i, String (i + 1) + ". " + ScreamerAudioProcessor::getFactoryPreset (i).name, true, proc.currentPreset.load() == i);
    menu.addSubMenu ("Factory presets", factory);
    PopupMenu load, save;
    for (int slot = 1; slot <= 9; ++slot)
    {
        const bool exists = proc.hasUserPreset (slot);
        load.addItem (200 + slot, "User " + String (slot) + (exists ? "" : "  (empty)"), exists, proc.currentPreset.load() == 100 + slot);
        save.addItem (300 + slot, "User " + String (slot) + (exists ? "  (overwrite)" : ""));
    }
    menu.addSubMenu ("Load user preset", load);
    menu.addSubMenu ("Save user preset", save);
    menu.addSeparator();

    PopupMenu gate;
    const int gNow = jlimit (0, 3, roundToInt (proc.rawAt (ScreamerAudioProcessor::rGate)));
    const char* gateHelp[4] = { "Off (default, like the original pedal)", "Light", "Medium", "Strong (noisy pickups / hum)" };
    for (int i = 0; i < 4; ++i) gate.addItem (50 + i, gateHelp[i], true, gNow == i);
    menu.addSubMenu ("Noise gate", gate);

    PopupMenu settings;
    settings.addItem (41, "MIDI footswitch latching (127 = on / 0 = off)", true, proc.rawAt (ScreamerAudioProcessor::rMidiFsMode) < 0.5f);
    settings.addItem (42, "MIDI footswitch momentary (toggle each press)", true, proc.rawAt (ScreamerAudioProcessor::rMidiFsMode) > 0.5f);
    menu.addSubMenu ("Settings", settings);

    PopupMenu midi;
    for (int i = 0; i < ScreamerAudioProcessor::numLearn; ++i)
        midi.addItem (1000 + i, "Learn: " + String (ScreamerAudioProcessor::learnDef (i).name) + " (" + ccText (i) + ")", true, lt == i);
    midi.addSeparator();
    if (lt >= 0) midi.addItem (1200, "Cancel MIDI learn");
    midi.addItem (1201, "Clear all MIDI assignments");
    midi.addSeparator();
    midi.addItem (910, "CC n+32 = fine (14-bit) for knobs on CC 0-31", false);
    midi.addItem (911, "Program Change 1-" + String (ScreamerAudioProcessor::getNumFactoryPresets()) + "  Factory presets", false);
    menu.addSubMenu ("MIDI", midi);
    menu.addSeparator();
    menu.addItem (999, "Screamer overdrive v" + String (JucePlugin_VersionString) + " - NINE HANDS | DSP", false);

    menu.setLookAndFeel (&menuLnf);
    menu.showMenuAsync (PopupMenu::Options().withMousePosition(),       // menu clic droit : toujours la ou l'on clique
        [safe = Component::SafePointer<ScreamerAudioProcessorEditor> (this)] (int r)
        {
            if (safe == nullptr || r == 0) return;
            auto& ed = *safe;
            auto& pr = ed.proc;
            if      (r >= 1 && r < 1 + numSizes) ed.setScaledHeight (ed.sizeHeight (r - 1));
            else if (r >= 20 && r < 20 + numSizes)
            {
                WigaWindowSize::setDefaultIndex (JucePlugin_Name, r - 20);   // toutes les nouvelles fenetres de ce plugin
                ed.setScaledHeight (ed.sizeHeight (r - 20));                // et cette fenetre tout de suite
            }
            else if (r == 41) pr.setParamValue ("midiFsMode", 0.0f);
            else if (r == 42) pr.setParamValue ("midiFsMode", 1.0f);
            else if (r >= 50 && r <= 53) pr.setParamValue ("gate", (float) (r - 50));
            else if (r >= 100 && r < 200) pr.applyFactoryPreset (r - 100);
            else if (r > 200 && r < 300)  pr.loadUserPreset (r - 200);
            else if (r > 300 && r < 400)  pr.saveUserPreset (r - 300);
            else if (r >= 1000) { ed.handleMidiMenu (r); return; }
            ed.showStatus();
        });
}
