#pragma once
//==============================================================================
// SCREAMER (NINE HANDS | DSP) - moteur audio, sans dependance JUCE (testable hors plugin).
//
// Reproduction de l'Ibanez TS9 Tube Screamer, modele du circuit etage par etage
// (valeurs du TS808 / TS9, analyses Electrosmash, Geofex, D. Yeh - DAFx 2007) :
//
//  IN -> tampon d'entree (Q1 2SC1815 suiveur, liaison 20 nF sur ~446 k : passe-haut ~18 Hz)
//     -> liaison 1 uF / 10 k (passe-haut ~16 Hz)
//     -> [sur-echantillonnage x4]
//     -> ETAGE D'ECRETAGE (JRC4558 non inverseur) :
//          vers la masse : 4,7 k + 47 nF (seules les frequences au-dessus de ~720 Hz sont amplifiees :
//          le grave passe a gain 1, propre -> c'est le « mid hump » et le grave serre du Tube Screamer)
//          contre-reaction : (51 k + DRIVE 500 k log) // 51 pF // 2 diodes 1S1588 tete-beche
//          sortie = entree + tension aux bornes des diodes : le signal propre se melange a l'ecretage doux
//          resolu a chaque echantillon (trapezes + Newton, equation de Shockley des diodes)
//     -> [decimation]
//     -> TONE : 1 k / 220 nF (passe-bas 723 Hz) + etage actif du 2e ampli op (pot 20 k, 220 ohms + 220 nF
//          au curseur, 10 k, 1 k de contre-reaction) : fonction de transfert exacte du 2e ordre, transformee bilineaire
//     -> LEVEL (pot 100 k log) -> tampon de sortie TS9 (470 ohms / 100 k) -> OUT
//
// Echantillons en volts (guitare ~ 0,1 a 0,5 V crete).
//==============================================================================

#include <cmath>
#include <vector>
#include <algorithm>
#include <cstring>

namespace screamer
{
    constexpr double pi = 3.14159265358979323846;

    inline float clampf (float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }
    inline float dbToGain (float db) { return std::pow (10.0f, db * 0.05f); }

    //--------------------------------------------------------------------------
    struct Biquad
    {
        double b0 = 1, b1 = 0, b2 = 0, a1 = 0, a2 = 0;
        double z1 = 0, z2 = 0;

        void set (double nb0, double nb1, double nb2, double na0, double na1, double na2)
        {
            b0 = nb0 / na0; b1 = nb1 / na0; b2 = nb2 / na0; a1 = na1 / na0; a2 = na2 / na0;
        }
        void lowpass (double sr, double fc, double q = 0.7071)
        {
            fc = std::min (std::max (fc, 10.0), sr * 0.45);
            const double w = 2 * pi * fc / sr, c = std::cos (w), al = std::sin (w) / (2 * q);
            set ((1 - c) / 2, 1 - c, (1 - c) / 2, 1 + al, -2 * c, 1 - al);
        }
        void highpass (double sr, double fc, double q = 0.7071)
        {
            fc = std::min (std::max (fc, 5.0), sr * 0.45);
            const double w = 2 * pi * fc / sr, c = std::cos (w), al = std::sin (w) / (2 * q);
            set ((1 + c) / 2, -(1 + c), (1 + c) / 2, 1 + al, -2 * c, 1 - al);
        }
        void peak (double sr, double fc, double q, double db)
        {
            fc = std::min (std::max (fc, 10.0), sr * 0.45);
            const double A = std::pow (10.0, db / 40.0);
            const double w = 2 * pi * fc / sr, c = std::cos (w), al = std::sin (w) / (2 * q);
            set (1 + al * A, -2 * c, 1 - al * A, 1 + al / A, -2 * c, 1 - al / A);
        }
        void lowShelf (double sr, double fc, double db, double s = 0.8)
        {
            fc = std::min (std::max (fc, 10.0), sr * 0.45);
            const double A = std::pow (10.0, db / 40.0);
            const double w = 2 * pi * fc / sr, c = std::cos (w), sn = std::sin (w);
            const double al = sn / 2 * std::sqrt ((A + 1 / A) * (1 / s - 1) + 2), sa = 2 * std::sqrt (A) * al;
            set (A * ((A + 1) - (A - 1) * c + sa), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sa),
                 (A + 1) + (A - 1) * c + sa, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sa);
        }
        void highShelf (double sr, double fc, double db, double s = 0.8)
        {
            fc = std::min (std::max (fc, 10.0), sr * 0.45);
            const double A = std::pow (10.0, db / 40.0);
            const double w = 2 * pi * fc / sr, c = std::cos (w), sn = std::sin (w);
            const double al = sn / 2 * std::sqrt ((A + 1 / A) * (1 / s - 1) + 2), sa = 2 * std::sqrt (A) * al;
            set (A * ((A + 1) + (A - 1) * c + sa), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sa),
                 (A + 1) - (A - 1) * c + sa, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sa);
        }
        inline float process (float xf) noexcept
        {
            const double x = xf;
            const double y = b0 * x + z1;
            z1 = b1 * x - a1 * y + z2;
            z2 = b2 * x - a2 * y;
            return (float) y;
        }
        void reset() { z1 = z2 = 0; }
    };

    struct OnePole   // passe-bas / passe-haut du 1er ordre
    {
        float a = 0, z = 0;
        void setLP (double sr, double fc) { a = (float) std::exp (-2 * pi * fc / sr); }
        inline float lp (float x) noexcept { z = x + a * (z - x); return z; }
        inline float hp (float x) noexcept { z = x + a * (z - x); return x - z; }
        void reset() { z = 0; }
    };

    // Lissage a 2 poles (deux 1er ordre en cascade) : pas de marche d'escalier
    struct Smooth2
    {
        float c = 0.01f, s1 = 0, s2 = 0;
        void setTime (double sr, double ms) { c = (float) (1.0 - std::exp (-1.0 / (ms * 0.001 * sr))); }
        void reset (float v) { s1 = s2 = v; }
        inline float next (float target) noexcept { s1 += (target - s1) * c; s2 += (s1 - s2) * c; return s2; }
        bool settled (float target) const { return std::abs (s2 - target) < 1.0e-5f && std::abs (s1 - target) < 1.0e-5f; }
    };

    //--------------------------------------------------------------------------
    // Sur-echantillonnage x4 : filtre RIF a phase lineaire (sinc fenetre de Kaiser)
    // en polyphase pour la montee et la descente.
    struct Oversampler4
    {
        static constexpr int factor = 4;
        static constexpr int taps = 128;          // multiple de 4
        float h[taps] {};
        float hist[taps * 2] {};                  // ligne a retard (entree x4) doublee pour lecture contigue
        int   pos = 0;
        float upHist[taps / factor * 2] {};
        int   upPos = 0;

        static double bessel0 (double x)
        {
            double s = 1, t = 1;
            for (int k = 1; k < 30; ++k) { t *= (x / (2 * k)) * (x / (2 * k)); s += t; }
            return s;
        }

        void design()
        {
            const double fc = 0.5 / factor * 0.90;   // coupure ~ 0,45 x Fs d'origine
            const double beta = 8.6;
            double sum = 0;
            for (int n = 0; n < taps; ++n)
            {
                const double m = n - (taps - 1) * 0.5;
                const double x = 2 * fc * m;
                const double sinc = std::abs (x) < 1e-12 ? 1.0 : std::sin (pi * x) / (pi * x);
                const double r = 2.0 * n / (taps - 1) - 1.0;
                const double w = bessel0 (beta * std::sqrt (std::max (0.0, 1 - r * r))) / bessel0 (beta);
                h[n] = (float) (2 * fc * sinc * w);
                sum += h[n];
            }
            for (auto& v : h) v = (float) (v / sum);
            reset();
        }
        void reset()
        {
            std::fill (std::begin (hist), std::end (hist), 0.0f);
            std::fill (std::begin (upHist), std::end (upHist), 0.0f);
            pos = upPos = 0;
        }
        // latence totale (montee + descente) en echantillons a la frequence d'origine
        static double latency() { return (taps - 1) / (double) factor; }

        // 1 echantillon -> 4 echantillons
        inline void up (float x, float* out) noexcept
        {
            constexpr int L = taps / factor;
            upPos = (upPos + L - 1) % L;
            upHist[upPos] = x; upHist[upPos + L] = x;
            const float* hp = upHist + upPos;
            for (int ph = 0; ph < factor; ++ph)
            {
                float acc = 0;
                for (int k = 0; k < L; ++k)
                    acc += h[k * factor + ph] * hp[k];
                out[ph] = acc * factor;
            }
        }
        // 4 echantillons -> 1 echantillon
        inline float down (const float* in) noexcept
        {
            for (int i = 0; i < factor; ++i)
            {
                pos = (pos + taps - 1) % taps;
                hist[pos] = in[i]; hist[pos + taps] = in[i];
            }
            const float* hp = hist + pos;
            float acc = 0;
            for (int k = 0; k < taps; ++k)
                acc += h[k] * hp[k];
            return acc;
        }
    };
}   // namespace screamer (outils)

namespace screamer
{
    //--------------------------------------------------------------------------
    // Courbes des potentiometres
    //--------------------------------------------------------------------------
    // potentiometre logarithmique (courbe « A » des pots japonais d'origine) : 15 % de la resistance a mi-course
    inline double audioTaper (double x)
    {
        constexpr double b = 32.11;                  // (b^x - 1) / (b - 1) vaut 0,15 a x = 0,5
        x = std::min (1.0, std::max (0.0, x));
        return (std::pow (b, x) - 1.0) / (b - 1.0);
    }

    //--------------------------------------------------------------------------
    // Etage d'ecretage du TS9 (1re moitie du JRC4558), resolu a la frequence sur-echantillonnee
    //--------------------------------------------------------------------------
    struct ClipStage
    {
        // composants (TS808 / TS9)
        static constexpr double R4 = 4.7e3, C3 = 47e-9;      // branche vers la masse : passe-haut ~720 Hz
        static constexpr double R6 = 51e3, C4 = 51e-12;      // contre-reaction
        static constexpr double Pdrive = 500e3;               // DRIVE 500 k log
        // diode 1S1588 (equivalente 1N4148 / 1N914)
        static constexpr double Is = 2.52e-9, nVt = 1.752 * 0.025852;
        static constexpr double rail = 3.4;                   // excursion de sortie du 4558 en 9 V (autour de 4,5 V)

        double T = 1.0 / 192000.0, k = 0, gc = 0;
        double vc = 0, ic3 = 0;          // condensateur C3 (tension, courant precedent)
        double vd = 0, icap = 0;         // tension aux bornes du reseau de contre-reaction, courant de C4
        double rf = R6;

        void prepare (double srO)
        {
            T = 1.0 / srO;
            k = T / (2.0 * C3);
            gc = 2.0 * C4 / T;
            reset();
        }
        void reset() { vc = ic3 = vd = icap = 0.0; }

        void setDrive (double knob01) { rf = R6 + Pdrive * audioTaper (knob01); }

        inline double process (double vp) noexcept
        {
            // courant dans 4,7 k + 47 nF (l'ampli op impose v- = v+)
            const double vcPrev = vc + k * ic3;
            const double i = (vp - vcPrev) / (R4 + k);
            ic3 = i;
            vc = vcPrev + k * i;

            // reseau de contre-reaction : C4 // (R6 + DRIVE) // diodes tete-beche ; inconnue : vd
            //   gc*vd - h + vd/rf + 2 Is sinh(vd / nVt) = i
            const double h = gc * vd + icap;
            const double g = gc + 1.0 / rf;
            double v = vd;
            for (int it = 0; it < 24; ++it)
            {
                const double a = v / nVt;
                const double e = std::exp (std::min (40.0, std::max (-40.0, a)));
                const double sh = e - 1.0 / e, ch = e + 1.0 / e;
                const double f  = g * v - h + Is * sh - i;
                const double df = g + Is * ch / nVt;
                double dv = f / df;
                const double lim = 4.0 * nVt;                         // pas limite : convergence sure
                if (dv >  lim) dv =  lim;
                if (dv < -lim) dv = -lim;
                v -= dv;
                if (std::abs (dv) < 1.0e-10) break;
            }
            icap = gc * v - h;
            vd = v;

            // sortie de l'ampli op = v+ + vd, limitee par les rails (genou doux)
            double out = vp + v;
            const double ao = std::abs (out);
            if (ao > rail - 0.4)
                out = std::copysign ((rail - 0.4) + 0.4 * std::tanh ((ao - (rail - 0.4)) / 0.4), out);
            return out;
        }
    };

    //--------------------------------------------------------------------------
    // Etage TONE (2e moitie du JRC4558) : 1 k / 220 nF // 10 k a l'entree +, pot 20 k entre les entrees + et -,
    // 220 ohms + 220 nF du curseur a la masse, 1 k de la sortie a l'entree -.
    // H(s) = (1/Rs)(G + s(G.tau + Cz(1 + Rf/Rr))) / (Gs.G + s(Gs(G.tau + Cz) + Cs.G + Cz/Rl) + s^2 Cs(G.tau + Cz))
    //   G = 1/Rl + 1/Rr, Gs = 1/Rs + 1/Ri, tau = Rz.Cz  (Rl : cote entree +, Rr : cote entree -)
    //--------------------------------------------------------------------------
    struct ToneStage
    {
        static constexpr double Rs = 1e3, Cs = 0.22e-6, Ri = 10e3, Rz = 220.0, Cz = 0.22e-6, Rf = 1e3, P = 20e3;
        Biquad bq;
        double sr = 48000.0;

        // reponse analogique (pour le calcul de la courbe du potard)
        static double magDb (double t, double f)
        {
            const double Rl = std::max (10.0, P * t), Rr = std::max (10.0, P * (1.0 - t));
            const double G = 1.0 / Rl + 1.0 / Rr, Gs = 1.0 / Rs + 1.0 / Ri, tau = Rz * Cz;
            const double w = 2 * pi * f;
            const double nr = G / Rs, ni = w * (G * tau + Cz * (1.0 + Rf / Rr)) / Rs;
            const double dr = Gs * G - w * w * Cs * (G * tau + Cz);
            const double di = w * (Gs * (G * tau + Cz) + Cs * G + Cz / Rl);
            return 10.0 * std::log10 ((nr * nr + ni * ni) / (dr * dr + di * di));
        }

        void prepare (double sampleRate) { sr = sampleRate; bq.reset(); }

        // t : position electrique du curseur (0 = sombre, 1 = brillant)
        void setPosition (double t)
        {
            const double Rl = std::max (10.0, P * t), Rr = std::max (10.0, P * (1.0 - t));
            const double G = 1.0 / Rl + 1.0 / Rr, Gs = 1.0 / Rs + 1.0 / Ri, tau = Rz * Cz;
            const double b0 = G / Rs, b1 = (G * tau + Cz * (1.0 + Rf / Rr)) / Rs;
            const double a0 = Gs * G, a1 = Gs * (G * tau + Cz) + Cs * G + Cz / Rl, a2 = Cs * (G * tau + Cz);
            // transformee bilineaire, frequence pre-deformee a 1 kHz
            const double w0 = 2 * pi * 1000.0;
            const double K = w0 / std::tan (w0 / (2.0 * sr));
            const double K2 = K * K;
            bq.set (b0 + b1 * K, 2 * b0, b0 - b1 * K,
                    a0 + a1 * K + a2 * K2, 2 * a0 - 2 * a2 * K2, a0 - a1 * K + a2 * K2);
        }
        inline float process (float x) noexcept { return bq.process (x); }
    };

    //--------------------------------------------------------------------------
    // Courbe du potard TONE : la TS9 a un pot dont l'effet se concentre en fin de course ;
    // ici la position electrique est choisie pour que l'aigu (4 kHz) varie regulierement en dB
    // d'un bout a l'autre de la course, avec les memes extremes que la pedale.
    //--------------------------------------------------------------------------
    struct ToneTaper
    {
        static constexpr int N = 129;
        double table[N] {};
        void build()
        {
            const double f = 4000.0;
            const double lo = ToneStage::magDb (0.0, f), hi = ToneStage::magDb (1.0, f);
            for (int n = 0; n < N; ++n)
            {
                const double target = lo + (hi - lo) * (double) n / (N - 1);
                double a = 0.0, b = 1.0;
                for (int it = 0; it < 60; ++it)
                {
                    const double m = 0.5 * (a + b);
                    (ToneStage::magDb (m, f) < target ? a : b) = m;
                }
                table[n] = 0.5 * (a + b);
            }
            table[0] = 0.0; table[N - 1] = 1.0;
        }
        double map (double x01) const
        {
            const double p = std::min (1.0, std::max (0.0, x01)) * (N - 1);
            const int i = std::min (N - 2, (int) p);
            const double fr = p - i;
            return table[i] + (table[i + 1] - table[i]) * fr;
        }
    };

    //--------------------------------------------------------------------------
    struct Params
    {
        float drive = 5.0f, tone = 5.0f, level = 5.0f;   // 0..10 comme sur la pedale
        bool  active = true;
        int   gate = 0;                                  // 0 off, 1..3
    };

    class Channel
    {
    public:
        void prepare (double sampleRate, const ToneTaper* taper)
        {
            sr = sampleRate;
            os.design();
            clip.prepare (sr * Oversampler4::factor);
            tone.prepare (sr);
            tp = taper;
            // tampon d'entree : 20 nF sur ~446 k ; liaison 1 uF sur 10 k
            hpIn.setLP (sr, 1.0 / (2 * pi * 446e3 * 20e-9));
            hpC2.setLP (sr, 1.0 / (2 * pi * 10e3 * 1e-6));
            // sortie : liaison 10 uF sur 100 k (TS9) ; derive negligeable, retire le continu
            hpOut.setLP (sr, 3.0);
            reset();
        }
        void reset()
        {
            os.reset(); clip.reset(); tone.bq.reset();
            hpIn.reset(); hpC2.reset(); hpOut.reset();
        }
        void setDrive (double d01) { clip.setDrive (d01); }
        void setTone (double t01)  { tone.setPosition (tp != nullptr ? tp->map (t01) : t01); }

        inline float process (float x) noexcept
        {
            const float vin = hpC2.hp (hpIn.hp (x));
            float up[Oversampler4::factor];
            os.up (vin, up);
            for (int i = 0; i < Oversampler4::factor; ++i)
                up[i] = (float) clip.process (up[i]);
            const float c = os.down (up);
            return hpOut.hp (tone.process (c));
        }

    private:
        double sr = 48000.0;
        Oversampler4 os;
        ClipStage clip;
        ToneStage tone;
        const ToneTaper* tp = nullptr;
        OnePole hpIn, hpC2, hpOut;
    };

    //--------------------------------------------------------------------------
    class Engine
    {
    public:
        static constexpr int maxChannels = 2;

        void prepare (double sampleRate, int numChannels)
        {
            sr = sampleRate;
            nCh = std::min (maxChannels, std::max (1, numChannels));
            if (! taperReady) { taper.build(); taperReady = true; }
            for (auto& c : ch) c.prepare (sr, &taper);
            for (auto* s : { &sDrive, &sTone, &sLevel }) s->setTime (sr, 14.0);
            sActive.setTime (sr, 3.0);
            first = true;
            counter = 0;
            gateDetHP.highpass (sr, 110.0, 0.707);
            gateEnv = 0.0f; gateGain = 1.0f; gateOpen = true; gateHold = 0;
            gateRelEnv = (float) std::exp (-1.0 / (0.030 * sr));
            gateAtt    = (float) (1.0 - std::exp (-1.0 / (0.0008 * sr)));
            gateRel    = (float) (1.0 - std::exp (-1.0 / (0.150 * sr)));
            gateHoldLen = (int) (0.080 * sr);
            std::memset (dryLine, 0, sizeof (dryLine));
            dryPos = 0;
            dryDelay = latencyInt();
        }

        static double latencySamples() { return Oversampler4::latency(); }
        static int latencyInt() { return (int) std::lround (Oversampler4::latency()); }

        // LEVEL : pot 100 k log monte en diviseur (0 = coupe)
        static float levelGain (float knob)
        {
            const double l = audioTaper (knob / 10.0);
            return (float) l;
        }

        void process (float* const* io, int numSamples, const Params& p)
        {
            if (first)
            {
                sDrive.reset (p.drive); sTone.reset (p.tone); sLevel.reset (p.level);
                sActive.reset (p.active ? 1.0f : 0.0f);
                for (auto& c : ch) { c.setDrive (p.drive / 10.0); c.setTone (p.tone / 10.0); }
                appliedDrive = p.drive; appliedTone = p.tone;
                first = false;
            }

            for (int i = 0; i < numSamples; ++i)
            {
                const float dr  = sDrive.next (p.drive);
                const float tn  = sTone.next (p.tone);
                const float lv  = sLevel.next (p.level);
                const float act = sActive.next (p.active ? 1.0f : 0.0f);
                // circuit mis a jour toutes les 8 echantillons, seulement si un potard bouge (economie de CPU au repos)
                if ((counter++ & 7) == 0 && (std::abs (dr - appliedDrive) > 1.0e-5f || std::abs (tn - appliedTone) > 1.0e-5f))
                {
                    appliedDrive = dr; appliedTone = tn;
                    for (int c = 0; c < nCh; ++c) { ch[c].setDrive (dr / 10.0); ch[c].setTone (tn / 10.0); }
                }

                const float out = levelGain (lv) * outTrim;

                float gg = 1.0f;
                if (p.gate > 0)
                {
                    const float mono = nCh > 1 ? 0.5f * (io[0][i] + io[1][i]) : io[0][i];
                    const float d = std::abs ((float) gateDetHP.process (mono));
                    gateEnv = std::max (d, gateEnv * gateRelEnv);
                    static const float openDb[4] = { -200.0f, -74.0f, -66.0f, -56.0f };
                    const float thrOpen = std::pow (10.0f, openDb[std::min (3, p.gate)] * 0.05f), thrClose = thrOpen * 0.5f;
                    if (gateEnv > thrOpen)       { gateOpen = true; gateHold = gateHoldLen; }
                    else if (gateEnv < thrClose) { if (gateHold > 0) --gateHold; else gateOpen = false; }
                    const float tg = gateOpen ? 1.0f : 0.0f;
                    gateGain += (tg - gateGain) * (tg > gateGain ? gateAtt : gateRel);
                    gg = gateGain * gateGain;
                }
                else { gateGain = 1.0f; gateOpen = true; }

                for (int c = 0; c < nCh; ++c)
                {
                    const float x = io[c][i];
                    const float wet = ch[c].process (x) * out * gg;
                    float* dl = dryLine[c];
                    dl[dryPos] = x;
                    const float dry = dl[(dryPos + dryLen - dryDelay) % dryLen];
                    io[c][i] = safety (dry + (wet - dry) * act);
                }
                dryPos = (dryPos + 1) % dryLen;
            }
        }

        // calibrage : DRIVE / TONE / LEVEL a midi, guitare de 0,1 a 0,15 V crete -> niveau de la guitare seule (+-2 dB) ;
        // LEVEL a fond : +14 a +16 dB, pour pousser l'ampli (reglage metal « drive a 0, level a fond »)
        float outTrim = 2.0f;

    private:
        // v1.3 : plus de plafond a 0 dBFS (il ecrasait le reglage metal LEVEL a fond devant l'ampli). Le seul plafond est
        // celui de la pedale : l'excursion des amplis op et du tampon de sortie en 9 V, environ +-3,4 V (≈ +10,6 dBFS).
        // Le moteur du DAW travaille en virgule flottante : un simulateur d'ampli place apres recoit le signal chaud du hardware.
        static inline float safety (float x) noexcept
        {
            constexpr float knee = 3.0f, room = 0.4f;
            const float ax = std::abs (x);
            if (ax < knee) return x;
            return std::copysign (knee + room * std::tanh ((ax - knee) / room), x);
        }

        float gateEnv = 0.0f, gateGain = 1.0f, gateRelEnv = 0.999f, gateAtt = 0.03f, gateRel = 0.0002f;
        bool  gateOpen = true; int gateHold = 0, gateHoldLen = 3840;
        Biquad gateDetHP;

        double sr = 48000.0;
        int nCh = 2;
        static constexpr int dryLen = 64;
        float dryLine[maxChannels][dryLen] {};
        int dryPos = 0, dryDelay = 32;
        Channel ch[maxChannels];
        ToneTaper taper; bool taperReady = false;
        Smooth2 sDrive, sTone, sLevel, sActive;
        bool first = true;
        unsigned counter = 0;
        float appliedDrive = -1.0f, appliedTone = -1.0f;
    };
}
