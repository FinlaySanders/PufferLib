# Encoder channel activity

Three independently seeded CPU-policy trajectories per checkpoint, 4,000 decisions each. Sampled every eight decisions. Real-play coverage is limited, not a proof that a channel can never activate. Inventory statistics exclude empty slots; spell and entity pools require entities to be present. Rare means nonzero on fewer than 0.1% of sampled rows. Exact-zero and constant channels are reported separately.

| Policy | Branch | Width | Sampled rows | Always zero | Rare nonzero | Constant |
|---|---|---:|---:|---:|---:|---:|
| identify1b_s701 | local_mlp1 | 256 | 1500 | 0 | 0 | 0 |
| identify1b_s701 | local_mlp2 | 256 | 1500 | 0 | 0 | 0 |
| identify1b_s701 | terrain_mlp1 | 256 | 1500 | 1 | 1 | 1 |
| identify1b_s701 | terrain_mlp2 | 128 | 1500 | 8 | 1 | 8 |
| identify1b_s701 | stats_mlp | 64 | 1500 | 1 | 0 | 1 |
| identify1b_s701 | stats_raw_includes_intentional_zeros | 134 | 1500 | 64 | 2 | 66 |
| identify1b_s701 | messages_signed | 256 | 1500 | 0 | 0 | 0 |
| identify1b_s701 | spell_pool_when_present | 128 | 1016 | 90 | 0 | 128 |
| identify1b_s701 | inventory_pool | 128 | 1500 | 12 | 2 | 12 |
| identify1b_s701 | projection_relu | 1024 | 1500 | 0 | 1 | 0 |
| identify1b_s701 | monster_pool_when_present | 128 | 766 | 0 | 0 | 0 |
| identify1b_s701 | floor_item_pool_when_present | 128 | 1458 | 4 | 0 | 4 |
| identify1b_s701 | inventory_slot_all | 16 | 51059 | 0 | 0 | 0 |
| identify1b_s701 | inventory_mlp1_all | 64 | 51059 | 1 | 0 | 1 |
| identify1b_s701 | inventory_mlp2_all | 64 | 51059 | 6 | 6 | 6 |
| identify1b_s701 | inventory_slot_armour | 16 | 7970 | 1 | 0 | 1 |
| identify1b_s701 | inventory_mlp1_armour | 64 | 7970 | 11 | 4 | 11 |
| identify1b_s701 | inventory_mlp2_armour | 64 | 7970 | 41 | 6 | 41 |
| identify1b_s701 | inventory_slot_potions | 16 | 4044 | 1 | 0 | 1 |
| identify1b_s701 | inventory_mlp1_potions | 64 | 4044 | 10 | 0 | 10 |
| identify1b_s701 | inventory_mlp2_potions | 64 | 4044 | 48 | 0 | 48 |
| identify1b_s701 | inventory_slot_scrolls | 16 | 4468 | 0 | 0 | 0 |
| identify1b_s701 | inventory_mlp1_scrolls | 64 | 4468 | 9 | 1 | 9 |
| identify1b_s701 | inventory_mlp2_scrolls | 64 | 4468 | 52 | 0 | 52 |
| identify1b_s701 | inventory_slot_wands | 16 | 1232 | 2 | 0 | 2 |
| identify1b_s701 | inventory_mlp1_wands | 64 | 1232 | 26 | 0 | 26 |
| identify1b_s701 | inventory_mlp2_wands | 64 | 1232 | 63 | 0 | 63 |
| identify1b_s701 | inventory_slot_rings | 16 | 291 | 5 | 0 | 5 |
| identify1b_s701 | inventory_mlp1_rings | 64 | 291 | 51 | 0 | 51 |
| identify1b_s701 | inventory_mlp2_rings | 64 | 291 | 58 | 0 | 58 |
| idreplace1b_s701 | local_mlp1 | 256 | 1500 | 0 | 0 | 0 |
| idreplace1b_s701 | local_mlp2 | 256 | 1500 | 1 | 0 | 1 |
| idreplace1b_s701 | terrain_mlp1 | 256 | 1500 | 6 | 3 | 6 |
| idreplace1b_s701 | terrain_mlp2 | 128 | 1500 | 9 | 2 | 9 |
| idreplace1b_s701 | stats_mlp | 64 | 1500 | 1 | 0 | 1 |
| idreplace1b_s701 | stats_raw_includes_intentional_zeros | 134 | 1500 | 67 | 5 | 69 |
| idreplace1b_s701 | messages_signed | 256 | 1500 | 0 | 0 | 0 |
| idreplace1b_s701 | spell_pool_when_present | 128 | 755 | 106 | 0 | 128 |
| idreplace1b_s701 | inventory_pool | 128 | 1500 | 12 | 0 | 12 |
| idreplace1b_s701 | projection_relu | 1024 | 1500 | 4 | 1 | 4 |
| idreplace1b_s701 | monster_pool_when_present | 128 | 729 | 0 | 0 | 0 |
| idreplace1b_s701 | floor_item_pool_when_present | 128 | 1496 | 24 | 0 | 24 |
| idreplace1b_s701 | inventory_slot_all | 16 | 52562 | 0 | 0 | 0 |
| idreplace1b_s701 | inventory_mlp1_all | 64 | 52562 | 1 | 0 | 1 |
| idreplace1b_s701 | inventory_mlp2_all | 64 | 52562 | 6 | 0 | 6 |
| idreplace1b_s701 | inventory_slot_armour | 16 | 8375 | 1 | 0 | 1 |
| idreplace1b_s701 | inventory_mlp1_armour | 64 | 8375 | 13 | 2 | 13 |
| idreplace1b_s701 | inventory_mlp2_armour | 64 | 8375 | 44 | 0 | 44 |
| idreplace1b_s701 | inventory_slot_potions | 16 | 2969 | 1 | 0 | 1 |
| idreplace1b_s701 | inventory_mlp1_potions | 64 | 2969 | 19 | 0 | 19 |
| idreplace1b_s701 | inventory_mlp2_potions | 64 | 2969 | 47 | 0 | 47 |
| idreplace1b_s701 | inventory_slot_scrolls | 16 | 4862 | 2 | 0 | 2 |
| idreplace1b_s701 | inventory_mlp1_scrolls | 64 | 4862 | 21 | 0 | 21 |
| idreplace1b_s701 | inventory_mlp2_scrolls | 64 | 4862 | 42 | 0 | 42 |
| idreplace1b_s701 | inventory_slot_rings | 16 | 560 | 6 | 0 | 6 |
| idreplace1b_s701 | inventory_mlp1_rings | 64 | 560 | 42 | 0 | 42 |
| idreplace1b_s701 | inventory_mlp2_rings | 64 | 560 | 63 | 0 | 63 |
| idreplace1b_s701 | inventory_slot_wands | 16 | 1381 | 4 | 0 | 4 |
| idreplace1b_s701 | inventory_mlp1_wands | 64 | 1381 | 46 | 0 | 46 |
| idreplace1b_s701 | inventory_mlp2_wands | 64 | 1381 | 63 | 0 | 63 |

The raw-stats branch intentionally includes zeros (including superseded role/race/gender one-hots); those are not dead learned ReLU units. Replacement intentionally leaves the old additive discovery channel unused. See synthetic.json for broader controlled item inputs and structural nonnegative-input checks.
