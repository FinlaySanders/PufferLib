
## 15m512: 116,429 -> 228,340 (1.96x); full-stack control before the ladder 229,485 (drift -0.5%)
  step                 SPS     delta     pct  share  component
  L0_alloff        116,429                           stock engine, no GPU flags, 1 lane, no overlap, no priority, 32 workers
  L1_engine        182,697   +66,268  +56.9%    59%  + engine mt7 (bit-exact ladder, PGO)
  L2_gpukernels    208,157   +25,460  +13.9%    23%  + GPU fast kernels + entity fusions
  L3_lanes4        228,352   +20,195   +9.7%    18%  + Muon 4 lanes
  L4_gradoverlap   229,591    +1,239   +0.5%     1%  + gradient overlap, 32 connections
  L5_prio_block    228,431    -1,160   -0.5%    -1%  + inference priority, blocking waits
  L6_pool24pin     228,340       -91   -0.0%    -0%  + pool 24 workers, pinned

## 5m512: 122,826 -> 330,451 (2.69x); full-stack control before the ladder 328,991 (drift +0.4%)
  step                 SPS     delta     pct  share  component
  L0_alloff        122,826                           stock engine, no GPU flags, 1 lane, no overlap, no priority, 32 workers
  L1_engine        278,855  +156,029 +127.0%    75%  + engine mt7 (bit-exact ladder, PGO)
  L2_gpukernels    300,574   +21,719   +7.8%    10%  + GPU fast kernels + entity fusions
  L3_lanes4        299,254    -1,320   -0.4%    -1%  + Muon 4 lanes
  L4_gradoverlap   292,809    -6,445   -2.2%    -3%  + gradient overlap, 32 connections
  L5_prio_block    308,528   +15,719   +5.4%     8%  + inference priority, blocking waits
  L6_pool24pin     330,451   +21,923   +7.1%    11%  + pool 24 workers, pinned

## 15m2k: 129,859 -> 262,521 (2.02x); full-stack control before the ladder 262,826 (drift -0.1%)
  step                 SPS     delta     pct  share  component
  L0_alloff        129,859                           stock engine, no GPU flags, 1 lane, no overlap, no priority, 32 workers
  L1_engine        217,212   +87,353  +67.3%    66%  + engine mt7 (bit-exact ladder, PGO)
  L2_gpukernels    218,020      +808   +0.4%     1%  + GPU fast kernels + entity fusions
  L3_lanes4        215,963    -2,057   -0.9%    -2%  + Muon 4 lanes
  L4_gradoverlap   203,079   -12,884   -6.0%   -10%  + gradient overlap, 32 connections
  L5_prio_block    230,402   +27,323  +13.5%    21%  + inference priority, blocking waits
  L6_pool24pin     223,821    -6,581   -2.9%    -5%  + pool 24 workers, pinned
  L7_cohort        262,521   +38,700  +17.3%    29%  + cohort 16/32 x 128, 4 active, 64 steps

## 5m2k: 131,647 -> 322,865 (2.45x); full-stack control before the ladder 320,250 (drift +0.8%)
  step                 SPS     delta     pct  share  component
  L0_alloff        131,647                           stock engine, no GPU flags, 1 lane, no overlap, no priority, 32 workers
  L1_engine        234,896  +103,249  +78.4%    54%  + engine mt7 (bit-exact ladder, PGO)
  L2_gpukernels    236,697    +1,801   +0.8%     1%  + GPU fast kernels + entity fusions
  L3_lanes4        237,591      +894   +0.4%     0%  + Muon 4 lanes
  L4_gradoverlap   230,525    -7,066   -3.0%    -4%  + gradient overlap, 32 connections
  L5_prio_block    237,731    +7,206   +3.1%     4%  + inference priority, blocking waits
  L6_pool24pin     229,434    -8,297   -3.5%    -4%  + pool 24 workers, pinned
  L7_cohort        322,865   +93,431  +40.7%    49%  + cohort 16/32 x 128, 4 active, 64 steps

## 5m4k: 159,626 -> 350,011 (2.19x); full-stack control before the ladder 346,065 (drift +1.1%)
  step                 SPS     delta     pct  share  component
  L0_alloff        159,626                           stock engine, no GPU flags, 1 lane, no overlap, no priority, 32 workers
  L1_engine        252,413   +92,787  +58.1%    49%  + engine mt7 (bit-exact ladder, PGO)
  L2_gpukernels    257,025    +4,612   +1.8%     2%  + GPU fast kernels + entity fusions
  L3_lanes4        257,444      +419   +0.2%     0%  + Muon 4 lanes
  L4_gradoverlap   247,101   -10,343   -4.0%    -5%  + gradient overlap, 32 connections
  L5_prio_block    253,325    +6,224   +2.5%     3%  + inference priority, blocking waits
  L6_pool24pin     244,343    -8,982   -3.5%    -5%  + pool 24 workers, pinned
  L7_cohort        350,011  +105,668  +43.2%    56%  + cohort 16/32 x 128, 4 active, 64 steps

## 15m2k, second ordering (scheduling before GPU); baseline stock 129,859
  M1_engine        215,898   +86,039  +66.3%  stock + engine
  M2_sched         214,598    -1,300   -0.6%  + scheduling block (priority, waits, pool 24 pinned, cohort)
  M3_gpukernels    245,617   +31,019  +14.5%  + GPU fast kernels + entity fusions
  M4_lanes4        258,307   +12,690   +5.2%  + Muon 4 lanes
  M5_gradoverlap   262,271    +3,964   +1.5%  + gradient overlap, 32 connections
  ctrl_b           262,839      +568   +0.2%  full stack control after
