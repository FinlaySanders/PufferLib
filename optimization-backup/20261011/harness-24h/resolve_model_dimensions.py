from pathlib import Path
import re,ast,operator,json,hashlib
r=Path(__file__).resolve().parent;s=(r/'source/ocean/nethack/nethack.cu').read_text();defs={}
for declaration in re.findall(r'static constexpr int\s+([^;]+);',s):
 for entry in re.split(r',\s*(?=\w+\s*=)',declaration):
  name,expr=entry.split('=',1);defs[name.strip()]=expr.strip()
flags=json.loads((r/'weight_cast_v29-build.json').read_text())['flags']
assert all(x not in flags for x in ['-DNH_MSG128','-DNH_MSG_V4096','-DNH_NO_APANEL'])
# The last declarations for the message knobs are their default arms; the accessory panel uses #ifndef.
defs['NH_PACC_DIM']='4 * (NH_INV_HID + NH_SFEAT)'
cache={};ops={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.floordiv,ast.FloorDiv:operator.floordiv,ast.LShift:operator.lshift,ast.RShift:operator.rshift,ast.BitOr:operator.or_}
def ev(n):
 if isinstance(n,ast.Constant):return n.value
 if isinstance(n,ast.Name):return resolve(n.id)
 if isinstance(n,ast.BinOp) and type(n.op) in ops:return ops[type(n.op)](ev(n.left),ev(n.right))
 raise ValueError(ast.dump(n))
def resolve(k):
 if k not in cache:cache[k]=ev(ast.parse(defs[k],mode='eval').body)
 return cache[k]
out={k:resolve(k) for k in ['NH_CONCAT','NH_BL_FEAT','NH_MSG_HID','NH_MSG_VOCAB','NH_PACC_DIM']};print(out);assert out['NH_CONCAT']==1698
(r/'MODEL_DIMENSIONS.json').write_text(json.dumps(dict(dimensions=out,dependencies=cache,method='Scalar expression evaluation with active default message and accessory-panel arms, handles comma-separated declarations. Crosschecked with capturedmatrix18.',source_sha256=hashlib.sha256(s.encode()).hexdigest(),flags=flags),indent=2))
