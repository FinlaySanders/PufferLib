from pathlib import Path
import csv,json,statistics,collections
r=Path(__file__).resolve().parent
rows=list(csv.DictReader((r/'training_gemm_screen.csv').open()))
groups=collections.defaultdict(lambda:collections.defaultdict(list))
for row in rows:groups[row['shape']][int(row['index'])].append(row)
output={}
for shape,cases in groups.items():
 means={i:statistics.mean(float(x['microseconds']) for x in v) for i,v in cases.items()}
 control=statistics.mean([means[-1],means[-2]])
 best=min([i for i in means if i>=0],key=means.get)
 data=dict(control_us=control,control_drift_percent=100*(means[-2]/means[-1]-1),best_index=best,best_us=means[best],gain_percent=100*(control/means[best]-1),algorithms=[dict(index=i,mean_us=means[i],gain_percent=100*(control/means[i]-1),algo_id=int(v[0]['algo_id']),workspace=int(v[0]['workspace']),relative_l2=float(v[0]['rel_l2']),max_abs=float(v[0]['max_abs']),finite=all(x['finite']=='1' for x in v)) for i,v in cases.items()])
 output[shape]=data;print(shape,{k:v for k,v in data.items() if k!='algorithms'})
(r/'TRAINING_GEMM_SCREEN_SUMMARY.json').write_text(json.dumps(dict(shapes=output,scope='Hot-operand synthetic single-GEMM graph screen. Not full training SPS. Any selected algorithm needs a fresh reverse-order timing repeat and actual workload validation.'),indent=2))
