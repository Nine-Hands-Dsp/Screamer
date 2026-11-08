# Outil hors plugin : compile le processeur + la fenetre de SCREAMER sous Linux et exporte des captures PNG (apercu, notice)
cmake_minimum_required(VERSION 3.22)
project(ScreamerRender VERSION 1.3.2)
set(CMAKE_CXX_STANDARD 17)
add_subdirectory(${JUCE_DIR} JUCE)
set(W ${CMAKE_CURRENT_SOURCE_DIR}/../..)
juce_add_binary_data(ScreamerAssets SOURCES
  ${W}/background.png ${W}/glow_red.png ${W}/led_on.png ${W}/fs_refl.png ${W}/Poppins-Medium.ttf ${W}/Poppins-Bold.ttf ${W}/Poppins-Light.ttf ${W}/NineHandsLogo.svg)
juce_add_console_app(ScreamerRender PRODUCT_NAME "ScreamerRender")
target_sources(ScreamerRender PRIVATE main.cpp ${W}/PluginProcessor.cpp ${W}/PluginEditor.cpp)
target_include_directories(ScreamerRender PRIVATE ${W})
target_compile_definitions(ScreamerRender PRIVATE JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0 JUCE_ALSA=0 JUCE_JACK=0
  JUCE_USE_XRANDR=0 JUCE_USE_XINERAMA=0 JUCE_USE_XCURSOR=0 JUCE_USE_XSHM=0 JucePlugin_Name="Screamer" JucePlugin_Build_VST3=0
  JucePlugin_VersionString="1.3.2" JUCE_STANDALONE_APPLICATION=1 JUCE_MODAL_LOOPS_PERMITTED=1)
target_link_libraries(ScreamerRender PRIVATE ScreamerAssets juce::juce_audio_utils juce::juce_recommended_config_flags)
