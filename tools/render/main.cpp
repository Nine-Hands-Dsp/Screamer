// Captures PNG de la fenetre reelle de Screamer (meme code que le plugin), pour l'apercu et la notice.
#include "PluginProcessor.h"
#include "PluginEditor.h"
#include "BinaryData.h"
using namespace juce;
int main (int argc, char** argv)
{
    ScopedJuceInitialiser_GUI init;
    const String out = argc > 1 ? argv[1] : ".";
    ScreamerAudioProcessor proc;
    proc.prepareToPlay (48000.0, 256);
    std::unique_ptr<AudioProcessorEditor> ed (proc.createEditor());
    auto* sed = static_cast<ScreamerAudioProcessorEditor*> (ed.get());
    std::printf ("taille par defaut : %d x %d\n", ed->getWidth(), ed->getHeight());

    auto pump = [] (int n) { for (int i = 0; i < n; ++i) MessageManager::getInstance()->runDispatchLoopUntil (40); };
    auto shot = [&] (const String& name, int preset, bool active, bool status, int height)
    {
        sed->setScaledHeight (height);
        sed->forceRenderScale (2.0f);
        proc.applyFactoryPreset (preset);
        proc.setParamValue ("active", active ? 1.f : 0.f);
        AudioBuffer<float> b (2, 256); MidiBuffer m;
        for (int i = 0; i < 20; ++i) { b.clear(); proc.processBlock (b, m); }
        pump (30);
        if (status) proc.setParamValue ("drive", 6.4f);
        else pump (100);
        pump (12);
        auto img = ed->createComponentSnapshot (ed->getLocalBounds(), true, 2.0f);
        File f (out + "/" + name + ".png"); f.deleteFile();
        FileOutputStream os (f); PNGImageFormat().writeImageToStream (img, os);
        std::printf ("%s (%d x %d)\n", f.getFullPathName().toRawUTF8(), img.getWidth(), img.getHeight());
    };
    shot ("screamer_default", 0, true,  false, ScreamerAudioProcessorEditor::defaultH);
    shot ("screamer_status",  0, true,  true,  ScreamerAudioProcessorEditor::refH);
    shot ("screamer_bypass",  2, false, false, ScreamerAudioProcessorEditor::refH);
    shot ("screamer_full",    8, true,  false, ScreamerAudioProcessorEditor::refH);

    // rendu exact de la pedale seule, en action (effet actif, LED allumee, preset 1) : fenetre de 900 px de haut capturee en 2x
    {
        sed->setScaledHeight (900);
        sed->forceRenderScale (2.0f);
        proc.applyFactoryPreset (0);
        proc.setParamValue ("active", 1.f);
        AudioBuffer<float> b (2, 256); MidiBuffer m;
        for (int i = 0; i < 20; ++i) { b.clear(); proc.processBlock (b, m); }
        pump (140);
        auto img = ed->createComponentSnapshot (ed->getLocalBounds(), true, 1800.0f / (float) ed->getHeight());
        File f (out + "/screamer_exact.png"); f.deleteFile();
        FileOutputStream os (f); PNGImageFormat().writeImageToStream (img, os);
        std::printf ("%s (%d x %d)\n", f.getFullPathName().toRawUTF8(), img.getWidth(), img.getHeight());
    }

    // capture du menu clic droit (meme LookAndFeel que le plugin : design des menus d'Octopus)
    {
        NineHandsMenu::MenuLnf lf;
        lf.f.med  = Typeface::createSystemTypefaceFor (BinaryData::PoppinsMedium_ttf, BinaryData::PoppinsMedium_ttfSize);
        lf.f.bold = Typeface::createSystemTypefaceFor (BinaryData::PoppinsBold_ttf, BinaryData::PoppinsBold_ttfSize);
        lf.f.reg  = Typeface::createSystemTypefaceFor (BinaryData::PoppinsLight_ttf, BinaryData::PoppinsLight_ttfSize);
        struct It { const char* t; bool sep, sub, act, tick; };
        const It items[] = { { "MIDI Learn: Drive (\xe2\x80\x94)", 0, 0, 1, 0 }, { "Clear MIDI: Drive", 0, 0, 0, 0 }, { "", 1, 0, 1, 0 },
                             { "Plugin size", 0, 1, 1, 0 }, { "", 1, 0, 1, 0 }, { "Factory presets", 0, 1, 1, 0 }, { "Load user preset", 0, 1, 1, 0 },
                             { "Save user preset", 0, 1, 1, 0 }, { "", 1, 0, 1, 0 }, { "Noise gate", 0, 1, 1, 0 }, { "Settings", 0, 1, 1, 0 },
                             { "MIDI", 0, 1, 1, 0 }, { "", 1, 0, 1, 0 }, { "Screamer overdrive v" JucePlugin_VersionString " - NINE HANDS | DSP", 0, 0, 0, 0 } };
        int w = 0, h = 0;
        for (auto& i : items) { int iw, ih; lf.getIdealPopupMenuItemSize (String::fromUTF8 (i.t), i.sep, 32, iw, ih); w = jmax (w, iw); h += ih; }
        const int bd = lf.getPopupMenuBorderSize(); w += 2 * bd; h += 2 * bd;
        const float sc = 2.0f;
        Image img (Image::ARGB, roundToInt (w * sc), roundToInt (h * sc), true);
        Graphics g (img); g.addTransform (AffineTransform::scale (sc));
        lf.drawPopupMenuBackground (g, w, h);
        int y = bd; int k = 0;
        for (auto& i : items)
        {
            int iw, ih; lf.getIdealPopupMenuItemSize (String::fromUTF8 (i.t), i.sep, 32, iw, ih);
            lf.drawPopupMenuItem (g, { bd, y, w - 2 * bd, ih }, i.sep, i.act, k == 5, i.tick, i.sub, String::fromUTF8 (i.t), {}, nullptr, nullptr);
            y += ih; ++k;
        }
        File f (out + "/screamer_menu.png"); f.deleteFile();
        FileOutputStream os (f); PNGImageFormat().writeImageToStream (img, os);
        std::printf ("%s (%d x %d)\n", f.getFullPathName().toRawUTF8(), img.getWidth(), img.getHeight());
    }

    // test pedale d'expression : course 2..116 sur CC 21 (drive)
    {
        proc.ccMap[0].store (21);                       // assignation faite comme par le MIDI Learn
        auto sendCC = [&] (int v)
        {
            AudioBuffer<float> b (2, 256); MidiBuffer m; m.addEvent (MidiMessage::controllerEvent (1, 21, v), 0);
            proc.processBlock (b, m);
            for (int k = 0; k < 20; ++k) { MidiBuffer e; b.clear(); proc.processBlock (b, e); }
            pump (3);
            return proc.raw ("drive");
        };
        const float a = sendCC (2), c = sendCC (116), mid = sendCC (59);
        std::printf ("pedale 2..116 -> drive %.2f / %.2f, mi-course %.2f\n", a, c, mid);
    }
    ed.reset();
    return 0;
}
