# Fast protocol: 12 measured epochs after the mature plateau.
import make_ablate_specs as m
m.write('fast',[('5m512','primary',512,['--epochs=28','--start=16']),('15m2048','model',1024,['--epochs=44','--start=32']),
                ('5m2048','model',512,['--epochs=44','--start=32']),('15m512','primary',1024,['--epochs=28','--start=16'])])
