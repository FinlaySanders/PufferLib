from pathlib import Path
import subprocess,shutil
repo=Path('/puffertank/pufferlib');root=Path('/puffertank/experiments/inventory-supervised-20260914');root.mkdir(exist_ok=False)
tree=root/'source';subprocess.run(['git','clone','--shared',str(repo),str(tree)],check=True)
for name in ('resources','raylib-5.5_linux_amd64','vendor/fast-nle'):
 p=tree/name
 if p.exists():
  if p.is_dir():shutil.rmtree(p)
  else:p.unlink()
 p.parent.mkdir(parents=True,exist_ok=True);p.symlink_to(repo/name,target_is_directory=True)
f=tree/'ocean/nethack/nethack.h';s=f.read_text();needle='env->seed = 0xCAFEBEEFUL + (unsigned long)env->rng;';assert needle in s;s=s.replace(needle,needle+'\n    if (getenv("NH_DATA_SEED")) env->seed += strtoull(getenv("NH_DATA_SEED"), NULL, 10);');f.write_text(s)
f=tree/'ocean/nethack/nethack.cu';s=f.read_text();needle='    NH_MM_BR(&a->concat, &ew->proj_w, &a->out, ew->proj_b);\n    return a->out;';assert s.count(needle)==1
capture=r'''
    {
      static long call=0, written=0; static FILE *fp=NULL;
      const char *dest=getenv("NH_INV_CAPTURE");
      if (dest && ++call > 256 && call%16==0) {
        if (!fp) { fp=fopen(dest,"wb"); if(!fp) abort(); }
        float *ids=(float*)malloc(2*B*NH_INV*sizeof(float));
        precision_t *sf=(precision_t*)malloc(B*NH_INV*NH_SFEAT*sizeof(precision_t));
        precision_t *rp=(precision_t*)malloc(B*NH_INV*NH_INV_HID*sizeof(precision_t));
        precision_t *cc=(precision_t*)malloc(B*NH_CONCAT*sizeof(precision_t));
        precision_t *out=(precision_t*)malloc(B*ew->hidden*sizeof(precision_t));
        cudaMemcpyAsync(ids,a->inv_idx.data,B*NH_INV*sizeof(float),cudaMemcpyDeviceToHost,stream);
        cudaMemcpyAsync(ids+B*NH_INV,a->invt_idx.data,B*NH_INV*sizeof(float),cudaMemcpyDeviceToHost,stream);
        cudaMemcpyAsync(sf,a->inv_sfeat.data,B*NH_INV*NH_SFEAT*sizeof(precision_t),cudaMemcpyDeviceToHost,stream);
        cudaMemcpyAsync(rp,a->inv_out.data,B*NH_INV*NH_INV_HID*sizeof(precision_t),cudaMemcpyDeviceToHost,stream);
        cudaMemcpyAsync(cc,a->concat.data,B*NH_CONCAT*sizeof(precision_t),cudaMemcpyDeviceToHost,stream);
        cudaMemcpyAsync(out,a->out.data,B*ew->hidden*sizeof(precision_t),cudaMemcpyDeviceToHost,stream);
        if(cudaStreamSynchronize(stream)!=cudaSuccess) abort();
        int cols=2*NH_INV+NH_INV*NH_SFEAT+NH_INV*NH_INV_HID+NH_MINV_DIM+ew->hidden;
        float *row=(float*)malloc(cols*sizeof(float));
        for(int b=0;b<B;b++) {
          int j=0;
          for(int k=0;k<NH_INV;k++) row[j++]=ids[b*NH_INV+k];
          for(int k=0;k<NH_INV;k++) row[j++]=ids[B*NH_INV+b*NH_INV+k];
          for(int k=0;k<NH_INV*NH_SFEAT;k++) row[j++]=(float)sf[b*NH_INV*NH_SFEAT+k];
          for(int k=0;k<NH_INV*NH_INV_HID;k++) row[j++]=(float)rp[b*NH_INV*NH_INV_HID+k];
          for(int k=0;k<NH_MINV_DIM;k++) row[j++]=(float)cc[b*NH_CONCAT+NH_MINV_OFF+k];
          for(int k=0;k<ew->hidden;k++) row[j++]=(float)out[b*ew->hidden+k];
          assert(j==cols);if(fwrite(row,sizeof(float),cols,fp)!=(size_t)cols) abort();
          written++;
        }
        fflush(fp);free(ids);free(sf);free(rp);free(cc);free(out);free(row);
        if(written>=atol(getenv("NH_INV_FRAMES"))) {
          fprintf(stderr,"CAPTURE_DONE frames=%ld cols=%d inv_dim=%d hidden=%d\n",written,cols,NH_MINV_DIM,ew->hidden);
          fclose(fp);_Exit(0);
        }
      }
    }
'''
s=s.replace(needle,needle.replace('    return a->out;',capture+'\n    return a->out;'));f.write_text(s)
(root/'capture.patch').write_bytes(subprocess.check_output(['git','-C',str(tree),'diff']))
shutil.copytree(repo/'config',root/'config');(root/'resources').symlink_to(repo/'resources',target_is_directory=True)
subprocess.run(['bash','build.sh','nethack'],cwd=tree,check=True)
shutil.copy2(tree/'puffer',root/'puffer');(root/'BUILD_DONE').write_text('ok\n')
