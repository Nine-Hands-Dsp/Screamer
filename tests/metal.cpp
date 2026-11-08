#include "../ScreamerDSP.h"
#include <cstdio>
using namespace screamer;
int main(){
  for (double amp : {0.1, 0.2, 0.4}) for (float lv : {5.f, 8.5f, 10.f}) {
    Engine e; e.prepare(48000,1); Params p; p.drive=0; p.tone=6.5f; p.level=lv;
    const int n=48000; std::vector<float> b(n);
    // accord de quinte grave + harmoniques (micro humbucker) avec decroissance
    for(int i=0;i<n;++i){ double t=i/48000.0, env=std::exp(-3*t);
      b[i]=(float)(amp*env*(0.6*std::sin(2*pi*82.4*t)+0.4*std::sin(2*pi*123.5*t)+0.3*std::sin(2*pi*329.6*t)+0.15*std::sin(2*pi*988*t)));}
    float* io[1]={b.data()}; e.process(io,n,p);
    float mx=0; for(float v:b) mx=std::max(mx,std::abs(v));
    std::printf("guitare %.1f V, level %.1f : crete sortie %.2f %s\n",amp,lv,mx, mx>0.94f?"(LIMITEUR 0,95 ACTIF)":"");
  }
}
