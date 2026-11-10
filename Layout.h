// genere par tools/make_art.py - ne pas modifier a la main (repere 617.5 x 900.0 = fond 1235 x 1800 px / 2)
#pragma once
#include <juce_graphics/juce_graphics.h>
namespace layout
{
    constexpr float frameW = 617.50f, frameH = 900.00f;   // pedale plein cadre (jacks aux bords gauche / droit)
    // ordre : drive, tone, level
    const juce::Point<float> knobPos[3] = { { 156.38f, 139.55f }, { 308.75f, 264.94f }, { 461.12f, 139.55f } };
    const float knobR[3] = { 60.67f, 47.53f, 60.67f };
    const juce::Point<float> ledPos { 308.75f, 681.57f }; const float ledS = 30.34f;
    const juce::Rectangle<float> glowRect { 197.51f, 570.34f, 222.47f, 222.47f };
    const juce::Point<float> fsPos { 308.75f, 778.65f }; const float footR = 38.31f, fsS = 192.13f;   // bouton / sprite
    const juce::Rectangle<float> statusRect { 90.18f, 560.22f, 437.14f, 44.49f }, presetRect { 90.18f, 560.22f, 437.14f, 44.49f };
    const float statusFont = 22.25f, presetFont = 22.25f;
    const juce::Rectangle<float> boxRect { 21.49f, 0.00f, 574.52f, 900.00f };   // boitier
    const float jackY = 558.00f;
    // serigraphie vectorielle : texte, police (0 medium, 1 bold, 2 light), taille em, espacement, centre, rotation (degres)
    struct Txt { const char* s; int font; float em, track, x, y, rot; };
    const Txt texts[] = {
        { "DRIVE", 0, 22.25f, 3.54f, 156.38f, 46.52f, 0.00f },
        { "TONE", 0, 22.25f, 3.54f, 308.75f, 185.06f, 0.00f },
        { "LEVEL", 0, 22.25f, 3.54f, 461.12f, 46.52f, 0.00f },
        { "SCREAMER", 1, 54.61f, 4.04f, 308.75f, 432.81f, 0.00f },
        { "OVERDRIVE", 2, 19.21f, 9.10f, 308.75f, 485.39f, 0.00f },
        { "OUT", 0, 17.19f, 2.02f, 47.78f, 558.00f, 90.00f },
        { "IN", 0, 17.19f, 2.02f, 569.72f, 558.00f, 90.00f }
    };
    struct Dot { float x, y, r; };
    const Dot dots[] = { { 120.48f, 201.73f, 1.82f }, { 94.20f, 175.45f, 1.82f }, { 84.58f, 139.55f, 1.82f }, { 94.20f, 103.65f, 1.82f }, { 120.48f, 77.37f, 1.82f }, { 156.38f, 67.75f, 1.82f }, { 192.28f, 77.37f, 1.82f }, { 218.56f, 103.65f, 1.82f }, { 228.17f, 139.55f, 1.82f }, { 218.56f, 175.45f, 1.82f }, { 192.28f, 201.73f, 1.82f }, { 279.42f, 315.74f, 1.82f }, { 257.96f, 294.27f, 1.82f }, { 250.10f, 264.94f, 1.82f }, { 257.96f, 235.62f, 1.82f }, { 279.42f, 214.15f, 1.82f }, { 308.75f, 206.29f, 1.82f }, { 338.08f, 214.15f, 1.82f }, { 359.54f, 235.62f, 1.82f }, { 367.40f, 264.94f, 1.82f }, { 359.54f, 294.27f, 1.82f }, { 338.08f, 315.74f, 1.82f }, { 425.22f, 201.73f, 1.82f }, { 398.94f, 175.45f, 1.82f }, { 389.33f, 139.55f, 1.82f }, { 398.94f, 103.65f, 1.82f }, { 425.22f, 77.37f, 1.82f }, { 461.12f, 67.75f, 1.82f }, { 497.02f, 77.37f, 1.82f }, { 523.30f, 103.65f, 1.82f }, { 532.92f, 139.55f, 1.82f }, { 523.30f, 175.45f, 1.82f }, { 497.02f, 201.73f, 1.82f } };
    const juce::Rectangle<float> rules[] = { { 152.73f, 484.48f, 55.30f, 1.82f }, { 409.47f, 484.48f, 55.30f, 1.82f } };
    const juce::Point<float> logoPos { 308.75f, 871.69f }; const float logoW = 198.20f;
}
