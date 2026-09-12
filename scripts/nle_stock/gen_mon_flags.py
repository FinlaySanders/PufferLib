# appends monster resistance / flag tables to nh_tables.h from the stock nle python package (public data, as the other tables)
from nle import nethack as n
mr = [n.permonst(i).mresists for i in range(n.NUMMONS)]
m1 = [n.permonst(i).mflags1 for i in range(n.NUMMONS)]
print("// monster mresists (MR_FIRE 1, MR_COLD 2, MR_SLEEP 4, MR_DISINT 8, MR_ELEC 16, MR_POISON 32, MR_ACID 64, MR_STONE 128) and mflags1 (M1_SEE_INVIS 0x01000000): the intrinsics a polymorphed hero gets from the form (set_uasmon PROPSET)")
print("static const unsigned NHT_MON_MR[NHT_NUMMONS] = {" + ",".join(str(x) for x in mr) + "};")
print("static const unsigned NHT_MON_M1[NHT_NUMMONS] = {" + ",".join(str(x) for x in m1) + "};")
