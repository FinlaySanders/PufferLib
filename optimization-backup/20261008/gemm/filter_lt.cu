#include "lt.cuh"
int main(int argc,char**argv){assert(argc==3);FILE*i=fopen(argv[1],"rb"),*o=fopen(argv[2],"wb");assert(i&&o);LtShape s;while(fread(&s,sizeof(s),1,i)==1)if(s.M>=1024&&s.N>=1024){assert(fwrite(&s,sizeof(s),1,o)==1);printf("KEPT %d %d %d %d %d\n",s.M,s.N,s.K,s.oa,s.ob);}fclose(i);fclose(o);}
