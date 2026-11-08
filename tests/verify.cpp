// Verifications du moteur SCREAMER contre les valeurs publiees (Electrosmash, Geofex, Yeh DAFx07)
#include "../ScreamerDSP.h"
#include <cstdio>
#include <complex>
using namespace screamer;
using cd = std::complex<double>;

// gain analytique de l'etage d'ecretage en petits signaux : 1 + Zf / Zi
static double clipGainDb (double f, double drive01)
{
    const cd s (0, 2 * pi * f);
    const double rf = ClipStage::R6 + ClipStage::Pdrive * audioTaper (drive01);
    const cd zf = 1.0 / (1.0 / rf + s * ClipStage::C4);
    const cd zi = ClipStage::R4 + 1.0 / (s * ClipStage::C3);
    return 20 * std::log10 (std::abs (1.0 + zf / zi));
}

int main()
{
    // 1. etage d'ecretage seul, petit signal (1 mV : diodes bloquees), sur-echantillonne x4 a 48 kHz
    std::printf ("1. Etage d'ecretage, gain petits signaux : modele / analytique (dB)\n");
    for (double d : { 0.0, 1.0 })
    {
        for (double f : { 100.0, 720.0, 2000.0, 5700.0, 12000.0 })
        {
            ClipStage c; c.prepare (192000.0); c.setDrive (d);
            double pk = 0;
            for (int i = 0; i < 192000; ++i)
            {
                const double y = c.process (0.001 * std::sin (2 * pi * f * i / 192000.0));
                if (i > 96000) pk = std::max (pk, std::abs (y));
            }
            std::printf ("   drive %.0f  %6.0f Hz : %6.2f / %6.2f\n", d * 10, f, 20 * std::log10 (pk / 0.001), clipGainDb (f, d));
        }
    }
    std::printf ("   gain mini / maxi a 1 kHz sans 51 pF ni 47 nF : %.1f / %.1f (Electrosmash : ~12 / ~118)\n",
                 1 + ClipStage::R6 / ClipStage::R4, 1 + (ClipStage::R6 + ClipStage::Pdrive) / ClipStage::R4);

    // 2. repliement : sinus 4 kHz fort, drive 10 -> energie hors harmoniques
    std::printf ("2. Repliement (drive 10, 0,3 V) : energie hors harmoniques / totale\n");
    for (double f : { 2000.0, 4000.0, 7000.0 })
    {
        Engine e; e.prepare (48000, 1); Params p; p.drive = 10; p.tone = 10; p.level = 5;
        const int n = 48000; std::vector<float> b (n);
        for (int i = 0; i < n; ++i) b[i] = (float) (0.3 * std::sin (2 * pi * f * i / 48000.0));
        float* io[1] = { b.data() }; e.process (io, n, p);
        // DFT grossiere sur 1 s : bins entiers (1 Hz)
        double tot = 0, harm = 0;
        for (int k = 20; k < 24000; k += 1)
        {
            double re = 0, im = 0;
            if (k % 10 != 0 && std::fmod (k, f) != 0) continue;     // echantillonnage des bins pour la vitesse
            for (int i = 24000; i < n; i += 1) { re += b[i] * std::cos (2 * pi * k * i / 48000.0); im -= b[i] * std::sin (2 * pi * k * i / 48000.0); }
            const double m = re * re + im * im; tot += m;
            if (std::fmod (k, f) == 0) harm += m;
        }
        std::printf ("   %5.0f Hz : %.2f %% (%.1f dB sous les harmoniques)\n", f, 100 * (tot - harm) / tot, 10 * std::log10 ((tot - harm) / harm + 1e-30));
    }

    // 3. bypass : nul parfait avec l'entree retardee de la latence
    {
        Engine e; e.prepare (48000, 1); Params p; p.active = false;
        const int n = 4800; std::vector<float> b (n), x (n);
        for (int i = 0; i < n; ++i) x[i] = b[i] = (float) (0.2 * std::sin (2 * pi * 440 * i / 48000.0));
        float* io[1] = { b.data() }; e.process (io, n, p);
        double err = 0; const int L = Engine::latencyInt();
        for (int i = L; i < n; ++i) err = std::max (err, (double) std::abs (b[i] - x[i - L]));
        std::printf ("3. Bypass : ecart maxi avec l'entree retardee de %d echantillons = %.2e\n", L, err);
    }

    // 4. frequences d'echantillonnage : stabilite et coherence du niveau (drive 5, 0,15 V, 440 Hz)
    std::printf ("4. Frequences d'echantillonnage (niveau de sortie, dB) :");
    for (double sr : { 44100.0, 48000.0, 96000.0, 192000.0 })
    {
        Engine e; e.prepare (sr, 2); Params p;
        const int n = (int) sr; std::vector<float> l (n), r (n);
        for (int i = 0; i < n; ++i) l[i] = r[i] = (float) (0.15 * std::sin (2 * pi * 440 * i / sr));
        float* io[2] = { l.data(), r.data() }; e.process (io, n, p);
        double s = 0; bool bad = false;
        for (int i = n / 2; i < n; ++i) { s += l[i] * l[i]; if (! std::isfinite (l[i])) bad = true; }
        std::printf ("  %.0f k : %+.2f%s", sr / 1000, 10 * std::log10 (s / (n / 2)) - 20 * std::log10 (0.15 / std::sqrt (2.0)), bad ? " NaN!" : "");
    }
    std::printf ("\n");

    // 5. signaux extremes : 2 V crete (sortie ligne), silence, impulsion
    {
        Engine e; e.prepare (48000, 1); Params p; p.drive = 10; p.level = 10;
        std::vector<float> b (48000);
        for (int i = 0; i < 48000; ++i) b[i] = (float) (2.0 * std::sin (2 * pi * 82.4 * i / 48000.0));
        b[100] = 10.0f;
        float* io[1] = { b.data() }; e.process (io, 48000, p);
        float mx = 0; bool bad = false;
        for (float v : b) { mx = std::max (mx, std::abs (v)); if (! std::isfinite (v)) bad = true; }
        std::printf ("5. Signal extreme (2 V + impulsion 10 V) : crete de sortie %.3f, %s\n", mx, bad ? "NaN !" : "stable");
    }
    return 0;
}
