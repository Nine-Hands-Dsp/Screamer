#include "../ScreamerDSP.h"
#include <cstdio>
using namespace screamer;
double run(Params p,double a){Engine e;e.prepare(48000,1);int n=48000;std::vector<float>b(n),x(n);
 for(int i=0;i<n;++i){double t=i/48000.0;x[i]=b[i]=(float)(a*(0.6*std::sin(2*pi*110*t)+0.4*std::sin(2*pi*330*t)+0.2*std::sin(2*pi*990*t)));}
 float*io[1]={b.data()};e.process(io,n,p);double s=0,r=0;for(int i=24000;i<n;++i){s+=b[i]*b[i];r+=x[i]*x[i];}return 10*std::log10(s/r);}
int main(){for(double a:{0.1,0.2}){std::printf("guitare %.1f V (drive 0, tone 5) :",a);for(float l:{5.f,6.7f,8.f,10.f}){Params p;p.drive=0;p.tone=5;p.level=l;std::printf("  level %.1f %+5.1f dB",l,run(p,a));}std::printf("\n");}}
