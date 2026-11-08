#include "../ScreamerDSP.h"
#include <chrono>
#include <cstdio>
using namespace screamer;
int main(){
  for (float d : {0.f, 5.f, 10.f}) {
    Engine e; e.prepare(48000,2); Params p; p.drive=d;
    const int n=48000*10; std::vector<float> L(n),R(n);
    for(int i=0;i<n;++i){ L[i]=R[i]=0.3f*std::sin(2*pi*110*i/48000.0)*std::exp(-(i%48000)/20000.0);}
    float* io[2]={L.data(),R.data()};
    auto t0=std::chrono::steady_clock::now();
    for(int o=0;o<n;o+=256) { float* b[2]={io[0]+o,io[1]+o}; e.process(b,256,p);}
    double s=std::chrono::duration<double>(std::chrono::steady_clock::now()-t0).count();
    std::printf("drive %.0f : %.1f %% d'un coeur (stereo 48 kHz)\n", d, 100*s/10.0);
  }
}
