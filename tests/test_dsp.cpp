// Tests hors plugin du moteur SCREAMER : g++ -O2 -std=c++17 -I.. test_dsp.cpp -o t && ./t
#include "../ScreamerDSP.h"
#include <cstdio>
using namespace screamer;

static double rmsDb (const std::vector<float>& v, size_t from)
{
    double s = 0; for (size_t i = from; i < v.size(); ++i) s += (double) v[i] * v[i];
    return 10 * std::log10 (s / (v.size() - from) + 1e-30);
}

static double run (Params p, double f, double amp, double* thd = nullptr)
{
    Engine e; const double sr = 48000; e.prepare (sr, 1);
    const int n = 48000; std::vector<float> b (n);
    for (int i = 0; i < n; ++i) b[i] = (float) (amp * std::sin (2 * pi * f * i / sr));
    float* io[1] = { b.data() };
    std::vector<float> in = b;
    e.process (io, n, p);
    if (thd)
    {
        // fondamental par correlation, reste = harmoniques
        double c = 0, s = 0; const int from = 24000;
        for (int i = from; i < n; ++i) { c += b[i] * std::cos (2 * pi * f * i / sr); s += b[i] * std::sin (2 * pi * f * i / sr); }
        const double a1 = 2 * std::sqrt (c * c + s * s) / (n - from);
        const double tot = std::pow (10, rmsDb (b, from) / 10) ;
        const double fund = a1 * a1 / 2;
        *thd = 100 * std::sqrt (std::max (0.0, tot - fund) / fund);
    }
    return rmsDb (b, 24000) - 20 * std::log10 (amp / std::sqrt (2.0));
}

int main()
{
    std::printf ("Reponse petits signaux (10 mV), gain dB, level 10 :\n      ");
    const double F[] = { 80, 150, 300, 500, 723, 1000, 2000, 3000, 5000, 8000 };
    for (double f : F) std::printf ("%6.0f", f);
    std::printf ("\n");
    for (float d : { 0.f, 5.f, 10.f })
        for (float t : { 0.f, 5.f, 10.f })
        {
            Params p; p.drive = d; p.tone = t; p.level = 10;
            std::printf ("d%2.0f t%2.0f", d, t);
            for (double f : F) std::printf ("%6.1f", run (p, f, 0.01));
            std::printf ("\n");
        }
    std::printf ("\nDistorsion (THD %%) et niveau a 1 kHz, tone 5, level 5 :\n");
    for (double a : { 0.02, 0.05, 0.1, 0.3, 0.6 })
    {
        std::printf ("amp %.2f V :", a);
        for (float d : { 0.f, 2.5f, 5.f, 7.5f, 10.f })
        {
            Params p; p.drive = d; p.tone = 5; p.level = 5; double thd;
            const double g = run (p, 1000, a, &thd);
            std::printf ("  d%.1f %+5.1fdB %5.1f%%", d, g, thd);
        }
        std::printf ("\n");
    }
    std::printf ("\nNiveau a 0,2 V (guitare), drive 0/5, tone 5, level de 0 a 10 :\n");
    for (float l = 0; l <= 10; l += 2.5f)
    {
        Params p; p.tone = 5; p.level = l; p.drive = 0; const double g0 = run (p, 440, 0.2);
        p.drive = 5; const double g5 = run (p, 440, 0.2);
        std::printf ("level %.1f : drive0 %+6.1f dB  drive5 %+6.1f dB\n", l, g0, g5);
    }
    std::printf ("\nCourbe TONE (4 kHz, gain dB du filtre seul) :");
    ToneTaper tt; tt.build();
    for (int k = 0; k <= 10; ++k) std::printf (" %.1f", ToneStage::magDb (tt.map (k / 10.0), 4000.0));
    std::printf ("\n");
    return 0;
}
