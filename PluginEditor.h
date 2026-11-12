#pragma once

#include "PluginProcessor.h"
#include <juce_gui_basics/juce_gui_basics.h>
#include "Layout.h"
#include "NineHandsMenu.h"
#include "NineHandsWindow.h"

//==============================================================================
// Potards (photo du kit, dans le fond : reflets fixes) ; seul le repere creme peint tourne.
//==============================================================================
class ScreamerKnobLookAndFeel : public juce::LookAndFeel_V4
{
public:
    void drawRotarySlider (juce::Graphics&, int x, int y, int w, int h,
                           float pos, float startAngle, float endAngle, juce::Slider&) override;
};

class ScreamerKnob : public juce::Slider
{
public:
    bool hitTest (int x, int y) override;
};

//==============================================================================
// Footswitch (photo du kit, dans le fond) : fonctionnement d'Echoflex : bascule a l'appui,
// bouton assombri tant qu'on appuie ; reflet rouge de la LED sur le flanc de l'ecrou, en fondu avec elle.
//==============================================================================
class FootSwitchArea : public juce::Component
{
public:
    explicit FootSwitchArea (juce::RangedAudioParameter& p);
    void paint (juce::Graphics&) override;
    void mouseDown (const juce::MouseEvent&) override;
    void mouseUp (const juce::MouseEvent&) override;
    bool hitTest (int x, int y) override;
    std::function<void()> onRightClick, onUserChange;
    juce::Image reflection;
    float ledLevel = 0.0f;
private:
    bool value = false, pressed = false;
    juce::ParameterAttachment attachment;
};

struct RightClickForwarder : public juce::MouseListener
{
    std::function<void (juce::Component*)> callback;
    void mouseDown (const juce::MouseEvent& e) override { if (e.mods.isPopupMenu() && callback) callback (e.eventComponent); }
};

//==============================================================================
class ScreamerAudioProcessorEditor : public juce::AudioProcessorEditor,
                                     private juce::Timer
{
public:
    explicit ScreamerAudioProcessorEditor (ScreamerAudioProcessor&);
    ~ScreamerAudioProcessorEditor() override;

    void paint (juce::Graphics&) override;
    void resized() override;
    void parentHierarchyChanged() override;
    void mouseDown (const juce::MouseEvent&) override;
    void mouseMove (const juce::MouseEvent&) override;
    void mouseExit (const juce::MouseEvent&) override;

    // Repere du fond (pedale plein cadre, image 965 x 1800 px / 2). Hauteurs de fenetre des pedales simples :
    // taille par defaut = taille minimale 493 px (« 60 % »), 100 % = 958 px, jusqu'a 150 %.
    static constexpr float baseW = layout::frameW;
    static constexpr float baseH = layout::frameH;
    static constexpr int defaultH = 493;
    static constexpr int refH = 958;
    static constexpr int maxH = refH * 3 / 2;

    void setScaledHeight (int h);
    void forceRenderScale (float sc) { forcedScale = sc; rebuildCaches (sc); }   // captures (outil de rendu) : caches a l'echelle de la capture
    static constexpr int numSizes = 3;          // 60 % (defaut d'origine) / 75 % / 100 %
    static int sizeHeight (int idx);
    void showStatus();

private:
    void timerCallback() override;
    void useSoftwareRenderer();
    void visibilityChanged() override;
    void askRepaint (juce::Rectangle<int> r);
    void showContextMenu (int learnIdx = -1);
public:
    juce::PopupMenu buildContextMenu (int learnIdx = -1);   // menu clic droit (aussi pour l'outil de controle des menus)
    void setGlowPercent (int pc);                            // clic droit > Glow intensity
private:
    void handleMidiMenu (int r);
    void showPresetMenu();
    void stepPreset (int delta);
    void rebuildCaches (float scale = 0.0f);
    float physicalScale() const;
    juce::Rectangle<int> scaled (juce::Rectangle<float> r) const;
    juce::String buildStatusLine() const;
    juce::String buildPresetLine() const;
    void drawPrint (juce::Graphics&);   // serigraphie vectorielle (textes, graduations, filets, logo)
    void buildPrint();
    void drawLed (juce::Graphics&);
    void drawPresetBar (juce::Graphics&);

    ScreamerAudioProcessor& proc;
    ScreamerKnobLookAndFeel lnf;
    RightClickForwarder rightClickFwd;

    juce::Image background, bgScaled, glow, glowS, ledOn;
    int cacheW = 0, cacheH = 0;
    float cacheScale = 0.0f, forcedScale = 0.0f;
    int resizeSettle = 0;
    // anti-gel v2 : suivi de la fenetre hote, de l'echelle et des redessins
    void* lastPeer = nullptr;
    double lastPaintMs = 0.0, repaintAskedMs = 0.0, lastScaleCheckMs = 0.0, lastRendererCheckMs = 0.0;
    juce::Typeface::Ptr labelFace, boldFace, lightFace;
    NineHandsMenu::MenuLnf menuLnf;        // menus clic droit au design d'Octopus
    NineHandsWindow::HostLock hostLock;    // fenetre du DAW : jamais sous 60 %, jamais au-dela de 150 %
    juce::Path printPath;                  // textes + graduations + filets, en unites du plugin
    std::unique_ptr<juce::Drawable> logo;

    ScreamerKnob knobs[ScreamerAudioProcessor::numKnobs];
    std::unique_ptr<juce::AudioProcessorValueTreeState::SliderAttachment> knobAtt[ScreamerAudioProcessor::numKnobs];
    FootSwitchArea footswitch;

    float ledLevel = 0.0f, drawnLed = -1.0f;
    int glowPc = 100;                      // clic droit > Glow intensity : halo de la LED (25 a 100 %, settings.xml)
    double lastGlowReadMs = 0.0;
    float glowAmt() const { return (float) glowPc / 100.0f; }
    int lastChanged = -1;
    float statusAlpha = 0.0f, drawnStatus = -1.0f;
    double statusUntil = 0.0;
    juce::String lastLine1, lastPreset;
    float lastValues[8];
    int lastPresetCounter = 0, lastMidiCount = 0, midiFlash = 0;
    int hoverZone = 0, drawnHover = -1;
    juce::String learnLine;
    double learnLineUntil = 0.0;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (ScreamerAudioProcessorEditor)
};
