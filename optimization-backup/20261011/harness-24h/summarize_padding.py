from pathlib import Path
import csv,json,statistics,collections
r=Path(__file__).resolve().parent;rows=list(csv.DictReader((r/'projection_padding_screen.csv').open()));groups=collections.defaultdict(lambda:collections.defaultdict(list))
for x in rows:groups[x['shape']][int(x['pad']),int(x['moves'])].append(x)
out={}
for shape,cases in groups.items():
 means={k:statistics.mean(float(x['microseconds']) for x in v) for k,v in cases.items()};base=statistics.mean([means[0,0],means[-1,0]])
 result=dict(control_us=base,control_drift_percent=100*(means[-1,0]/means[0,0]-1),cases=[dict(pad=k[0],moves=k[1],microseconds=us,gain_percent=100*(base/us-1),relative_l2=float(cases[k][0]['rel_l2']),max_abs=float(cases[k][0]['max_abs'])) for k,us in means.items()]);out[shape]=result
 print(shape,json.dumps(result),flush=True)
(r/'PROJECTION_PADDING_SUMMARY.json').write_text(json.dumps(dict(shapes=out,scope='Synthetic GEMM; moves=1 includes packing and output unpacking. moves=0 is only a ceiling. Logical model dimensions unchanged.'),indent=2))
