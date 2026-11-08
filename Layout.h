// genere par tools/make_art.py - ne pas modifier a la main (repere 760 x 958, fond 2x)
#pragma once
#include <juce_graphics/juce_graphics.h>
namespace layout
{
    // ordre : drive, tone, level
    const juce::Point<float> knobPos[3] = { { 262.00f, 158.00f }, { 380.00f, 268.00f }, { 498.00f, 158.00f } };
    const float knobR[3] = { 47.00f, 37.00f, 47.00f };
    const juce::Point<float> ledPos { 380.00f, 708.00f }; const float ledS = 30.00f;
    const juce::Rectangle<float> glowRect { 270.00f, 598.00f, 220.00f, 220.00f };
    const juce::Point<float> fsPos { 380.00f, 804.00f }; const float footR = 37.88f, fsS = 190.00f;   // bouton / sprite
    const juce::Rectangle<float> statusRect { 205.00f, 552.00f, 350.00f, 56.00f }, presetRect { 205.00f, 620.00f, 350.00f, 36.00f };
    const float statusFont = 28.00f, presetFont = 21.00f;
    const juce::Rectangle<float> boxRect { 150.00f, 34.00f, 460.00f, 890.00f };   // boitier (notice)
    const float jackY = 585.80f;
}
