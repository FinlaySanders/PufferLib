from pathlib import Path
import difflib
import hashlib
import json

r = Path(__file__).resolve().parent
old = json.loads((r/'IMMUTABLE_OBJECT_READS.json').read_text())
base = Path(old['source'])
before = {name:(base/name).read_text() for name in ['include/objclass.h','src/o_init.c']}
after = dict(before)
needle = '#define OBJ_NAME(obj) (obj_descr[(obj).oc_name_idx].oc_name)\n#define OBJ_DESCR(obj) (obj_descr[(obj).oc_descr_idx].oc_descr)'
assert after['include/objclass.h'].count(needle)==1
after['include/objclass.h'] = after['include/objclass.h'].replace(needle, '''#ifdef NLE_OBJECTS_GLOBAL
#define OBJ_NAME(obj) (obj_descr[(obj).oc_name_idx].oc_name)
#define OBJ_DESCR(obj) (obj_descr[(obj).oc_descr_idx].oc_descr)
#else
extern const char *nle_object_name(int index);
#define OBJ_NAME(obj) (nle_object_name((obj).oc_name_idx))
#define OBJ_DESCR(obj) (obj_descr_baseline[(obj).oc_descr_idx].oc_descr)
#endif''')
needle = '#include "lev.h" /* save & restore info */'
assert after['src/o_init.c'].count(needle)==1
after['src/o_init.c'] = after['src/o_init.c'].replace(needle, '''/* Fruit naming is the sole runtime mutation of the description table. */
const char *
nle_object_name(int index)
{
    return index == SLIME_MOLD ? obj_descr[index].oc_name
                              : obj_descr_baseline[index].oc_name;
}

''' + needle)
patch = ''.join(''.join(difflib.unified_diff(before[name].splitlines(True),after[name].splitlines(True),fromfile='a/'+name,tofile='b/'+name)) for name in before)
p = r/'SHARED_NAMES.patch'; assert not p.exists(); p.write_text(patch)
spec = dict(source=str(base), fields=old['fields'], files={name:dict(sha256=hashlib.sha256((base/name).read_bytes()).hexdigest()) for name in before}, hypothesis='Avoid private readonly string-descriptor table lookups; preserve per-game fruit-name override.', audit='Only runtime table assignment found is obj_descr[SLIME_MOLD].oc_name in options.c. Build-tool global path unchanged. Existing invariant smoke augmented with exact name/description pointer checks and a per-context fruit override.', status='Prepared, not applied or tested')
(r/'SHARED_NAMES.json').write_text(json.dumps(spec,indent=2))
driver=(r/'immutable_objects_screen.py').read_text().replace("r / 'immutable_objects'", "r / 'shared_names'").replace('IMMUTABLE_OBJECT_READS','SHARED_NAMES').replace("'immutable_'+name", "'shared_names_'+name").replace('BUILD immutable item reads', 'BUILD shared immutable names/descriptions').replace('IMMUTABLE OBJECT SCREEN COMPLETE', 'SHARED NAMES SCREEN COMPLETE')
(r/'shared_names_screen.py').write_text(driver)
print('Prepared shared name/description reads, with private fruit override. No source build yet.')
