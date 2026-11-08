// genere par tools/make_art.py - ne pas modifier a la main (repere 482.5 x 900.0 = fond 965 x 1800 px / 2)
#pragma once
#include <juce_graphics/juce_graphics.h>
namespace layout
{
    constexpr float frameW = 482.50f, frameH = 900.00f;   // pedale plein cadre (jacks aux bords gauche / droit)
    // ordre : drive, tone, level
    const juce::Point<float> knobPos[3] = { { 121.92f, 125.39f }, { 241.25f, 236.63f }, { 360.58f, 125.39f } };
    const float knobR[3] = { 47.53f, 37.42f, 47.53f };
    const juce::Point<float> ledPos { 241.25f, 681.57f }; const float ledS = 30.34f;
    const juce::Rectangle<float> glowRect { 130.01f, 570.34f, 222.47f, 222.47f };
    const juce::Point<float> fsPos { 241.25f, 778.65f }; const float footR = 38.31f, fsS = 192.13f;   // bouton / sprite
    const juce::Rectangle<float> statusRect { 64.28f, 523.82f, 353.93f, 56.63f }, presetRect { 64.28f, 592.58f, 353.93f, 36.40f };
    const float statusFont = 28.31f, presetFont = 21.24f;
    const juce::Rectangle<float> boxRect { 21.49f, 0.00f, 439.52f, 900.00f };   // boitier
    const float jackY = 558.00f;
}
