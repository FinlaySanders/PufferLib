from pathlib import Path
import json,subprocess,shutil,hashlib
here=Path(__file__).resolve().parent;repo=here.parents[3]
data=json.loads((here/'results.json').read_text());rows=data['rows'];values=[]
for width in [32,128,256]:
 values.append([next(r['primary_macro_auc'] for r in rows if r['kind']==kind and r['buckets']==v and r['width']==width) for kind,v in [('trigram',256),('trigram',1024),('trigram',4096),('cnn',0)]])
(here/'grid_data.h').write_text('static const double scores[3][4] = '+json.dumps(values).replace('[','{').replace(']','}')+';\n')
(here/'grid_manifest.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256((here/'results.json').read_bytes()).hexdigest(),rows_embedding_dimensions=[32,128,256],columns=['256 buckets','1024 buckets','4096 buckets','character CNN'],values=values,metric='median over three seeds of macro AUROC across five event tasks',colour_limits=[.95,1.0]),indent=2))
subprocess.run(['clang','-O2','-I.','-I./raylib-5.5_linux_amd64/include','-I./src','-I./vendor','-Iresources',str(here/'grid.c'),'resources/trailer/fonts.c','-o',str(here/'grid'),'raylib-5.5_linux_amd64/lib/libraylib.a','-lGL','-lm','-lpthread','-DPLATFORM_DESKTOP'],cwd=repo,check=True)
subprocess.run(['xvfb-run','-a',str(here/'grid')],cwd=repo,check=True)
subprocess.run(['python3','resources/article/webify.py'],cwd=repo,check=True,stdout=subprocess.DEVNULL)
for rel in ['message_encoder_grid.png','web/message_encoder_grid.png','web/message_encoder_grid.jpg']:shutil.copy2(repo/'resources/article/out'/rel,Path('/puffertank/docker/nethack_article')/rel)
