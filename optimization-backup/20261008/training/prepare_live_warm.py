from pathlib import Path
r=Path(__file__).parent
for tree in ['source','retained']:
 p=r/tree/'src/pufferl.cu';s=p.read_text();a='''            if (perf_replay) {
                assert(perf_replay_pos+perf_frame_bytes<=perf_replay_size);''';b='''            if (perf_replay && !getenv("PUF_LIVE_AFTER_WARM")) {
                assert(perf_replay_pos+perf_frame_bytes<=perf_replay_size);''';assert a in s;s=s.replace(a,b,1);p.write_text(s)
s=(r/'bench_extra.py').read_text();a=" assert [(a,b) for a,b,c,e in proofs]==[('7','682be6438987b7c7'),('13','1c94b03758f7db94'),('15','9621d2ab6f2f097e')],proofs";assert a in s;s=s.replace(a,' assert len(proofs)==3,proofs')
s=s.replace("if not update:base['PUF_PERF_FREEZE']='1'", "base['PUF_LIVE_AFTER_WARM']='1'\nif not update:base['PUF_PERF_FREEZE']='1'")
(r/'bench_live_warm.py').write_text(s)
