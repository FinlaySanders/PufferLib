import configparser
def load(f):
    c=configparser.ConfigParser(inline_comment_prefixes=("#",";"),strict=False,interpolation=None); c.read(f); return c
t=load("trials/sweep_1788689609318_0865.ini"); b=load("config/nethack.ini")
swept=set(s[len("sweep.env."):] for s in t.sections() if s.startswith("sweep.env."))
print("key | t865 | default | swept")
for k,v in t.items("env"):
    if any(x in k for x in ("coef","penalty","reward","bonus","scale","weight")):
        d=b.get("env",k,fallback="-").strip()
        print("%s | %s | %s | %s" % (k, v.strip(), d, "yes" if k in swept else "no"))
