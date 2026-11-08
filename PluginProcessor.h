#pragma once
#include <cstring>

#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_audio_utils/juce_audio_utils.h>
#include <atomic>
#include "ScreamerDSP.h"

//==============================================================================
// SCREAMER (NINE HANDS | DSP) - reproduction de l'overdrive Ibanez TS9 Tube Screamer.
// Voir README.md et ScreamerDSP.h.
//==============================================================================

struct ScreamerPreset
{
    const char* name;
    float drive, tone, level;   // 0..10 comme sur la pedale
};

class ScreamerAudioProcessor : public juce::AudioProcessor,
                               private juce::AsyncUpdater,
                               private juce::Timer
{
public:
    ScreamerAudioProcessor();
    ~ScreamerAudioProcessor() override = default;

    void prepareToPlay (double sampleRate, int samplesPerBlock) override;
    void releaseResources() override {}
    bool isBusesLayoutSupported (const BusesLayout&) const override;
    void processBlock (juce::AudioBuffer<float>&, juce::MidiBuffer&) override;
    using AudioProcessor::processBlock;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }
    const juce::String getName() const override { return "Screamer"; }
    bool acceptsMidi() const override  { return true; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return 0.0; }

    static int getNumFactoryPresets();
    static const ScreamerPreset& getFactoryPreset (int index);
    int getNumPrograms() override { return getNumFactoryPresets(); }
    int getCurrentProgram() override;
    void setCurrentProgram (int index) override { applyFactoryPreset (index); }
    const juce::String getProgramName (int index) override { return getFactoryPreset (index).name; }
    void changeProgramName (int, const juce::String&) override {}
    void applyFactoryPreset (int index);

    bool saveUserPreset (int slot);
    bool loadUserPreset (int slot);
    bool hasUserPreset (int slot) const;
    static juce::File getUserPresetFile();

    void getStateInformation (juce::MemoryBlock&) override;
    void setStateInformation (const void*, int) override;

    juce::AudioProcessorValueTreeState apvts;
    static juce::AudioProcessorValueTreeState::ParameterLayout createLayout();
    void setParamValue (const juce::String& id, float plain);

    // anti-gel : pointeurs des parametres mis en cache au demarrage (aucune recherche par chaine dans processBlock)
    enum RawIndex { rDrive, rTone, rLevel, rActive, rMidiFsMode, rGate, numRaw };
    float rawAt (int i) const { return rawPtr[i]->load (std::memory_order_relaxed); }
    float raw (const char* id) const
    {
        for (int i = 0; i < numRaw; ++i)
            if (std::strcmp (id, rawIds[i]) == 0) return rawAt (i);
        return apvts.getRawParameterValue (id)->load();
    }
    static constexpr const char* rawIds[numRaw] = { "drive", "tone", "level", "active", "midiFsMode", "gate" };
    std::atomic<float>* rawPtr[numRaw] {};

    static juce::StringArray gateNames() { return { "Off", "Light", "Medium", "Strong" }; }

    // ---- informations pour la fenetre ----
    std::atomic<int> currentPreset { 0 };      // >= 0 usine, 100 + n utilisateur, -1 = modifie
    std::atomic<int> presetCounter { 0 };
    std::atomic<int> lastMidiCC { -1 }, lastMidiValue { 0 }, lastMidiProgram { -1 }, midiCounter { 0 };

    static constexpr int numKnobs = 3;
    static const char* knobId (int i);

    // MIDI Learn : toutes les commandes de la facade (meme ordre que la file anti-gel)
    enum LearnType { learnContinuous, learnFootswitch };
    struct LearnDef { const char* id; const char* name; int type; };
    static constexpr int numLearn = 4;              // 0-2 potards, 3 footswitch
    static const LearnDef& learnDef (int i);
    std::atomic<int> ccMap[numLearn];
    std::atomic<int> learnTarget { -1 };
    std::atomic<int> lastLearned { -1 };
    void resetMidiMap();

private:
    void handleMidi (juce::MidiBuffer& midi);
    void setParamFromAudio (int queueIndex, float plain);   // thread audio : met en file, applique sur le thread de messages
    void timerCallback() override;                          // anti-gel : vide la file (aucun appel a l'hote depuis l'audio)
    static constexpr int numQueued = numLearn;
    std::atomic<float> pendingValue[numQueued];
    std::atomic<bool>  pendingSet[numQueued];
    void handleAsyncUpdate() override;
    float mapCC (int knob, float raw01);

    screamer::Engine engine;
    double sr = 48000.0;

    // pedale d'expression : rampe lineaire vers chaque nouvelle valeur sur l'intervalle mesure entre deux CC
    struct ExprRamp
    {
        bool  active = false;
        float value = 0.0f, target = 0.0f, step = 0.0f;
        int   left = 0;
        juce::int64 lastTime = 0;
        int   msb = -1;
        float lo = 1.0f, hi = 0.0f;
    } ramps[numKnobs];
    juce::int64 sampleClock = 0;
    int prevFsCC[numLearn] {};
    std::atomic<int> pendingPreset { -1 };

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (ScreamerAudioProcessor)
};
