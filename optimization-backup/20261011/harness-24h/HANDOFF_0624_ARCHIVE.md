# Active goal — 2026-10-10T05:52:15.379636+00:00

Read OBJECTIVE.txt and original attachment before continuing. Original24h window ends2026-10-10 22:30:39UTC (~16h40 remaining). Do not create anothergoal or finish early. Latestturn PROGRESS:several newcandidateclasses screened/closed. Production16files unchanged inintegrity_440min.json.

## Process state

No heavyprocess live; all sessions terminal:23135,69072(failedcompile),1919,50178,97618,25049,89044. Do not restart them. Currentisolatedsource andbinarypool_bwd_v35b, SHA73c3404ea50246cebb3635f4ac5203df2a4a98d59ce79bd887dd6606cc69ec35. Allnewflagsdefaultoff. No engine/production/defaultchanges orcommits/pushes. Buildwith -DPUF_MUON_OUTPLACE -lcuda.

## Established best remains unchanged

COMBINED_DIRECT_SUMMARY:194071.687→210221.722SPS,+8.322%INCLUDING24→32workers. Fixed24workers+3.896%. Memory8840→8290MiB,80replay/frozenactorproofsexact. GPUcombinedrounding changes; nolearningequivalenceclaim. DEPTH_COMBO_CONFIRM_SUMMARY:382949→397736,+3.861%,secondary4.31Mdepthmodel. Originaldetails inHANDOFF_0529_ARCHIVE.md. FastenvinPRIORITY_CANDIDATE.json; removePUF_ROLLOUT_DETAIL forheadline.

## Closed this turn

1. ENTITY_FUSED_FULL_SUMMARY: all4entityinferencefusion210? exactcontrols209817.493→211118.677,+.62015%,drift+.32645%. Actualfullinference+17.8765%,380416BF16outputsexactonsavedbatch,doesnottranslatetoatrainingwin. Parkstandaloneinference; no extendedupdates.
2. ENTITY_TRAIN_GPU_SUMMARY:969.743→941.807ms,+2.9663%,drift+.21374%. Inventory+1.715%,other3+1.264%. ENTITY_TRAIN_FULL_SUMMARY:control210091.241;trainingonly210766.656(+.32149%),training+inference211066.678(+.46429%);drift−.02631%. Rollouttail161.64→188.91/195.43msabsorbsGPUgain. All80obsproofs/frozenactors/countsmatch. Parkbothunder1%fullgate. ENTITY_TRAIN_PROOF.json prepared NOTRUN;do not runextendedproofsforlosers.
3. POOL_BWD_SCREEN:32smokes/56,252,160BF16gradientbits+biasint64exact. B1/17/512/4096,4branches,randommasks+all-padfirstgame. Inventory89.51→48.52us,monster31.18→14.05,item31.25→14.46,spell19.27→10.50. PureN/PAD/OFFspecializationalsotested,smallerwins. POOL_BWD_GPU_SUMMARY:control970.133ms;specialization968.786(+.139%),fused963.539(+.684%),drift+.14166%. Park,bothbelow1%GPUgate;nofull/extendedproofs.

## Implementation/artifacts

Trainingforward:entity_train_fused.py preservesBF16GEMMroundBEFOREbothbias/ReLUlayers,storesh1/vfororiginalbackward,thenTritonsum/max(firstmaxindex). Syntheticpooled/argmaxexact,butinventory11intermediateVvaluesdifferrelL2~4.9e-6;notuniversalexactness. 4096gamesstandalonereferenceusesprivate4MiBcuBLAS+separatebiaskernels. Filesentity_train_reference.cu/.so,entity_train_screen.py,export_entity_train_fused.py,prepare_entity_train_fused.py,ENTITY_TRAIN_FUSED.patch,ENTITY_TRAIN_EXPORT.json. EmbeddedSM89cubins source/src/entity_train_fused.cuh. NH_ENTITY_TRAIN_FUSEDbits1inv/2monster/4item/8spell;onlya->training&&!nh_fused_br_activewithdimensionguards;NH_ENT_LINPOOLfallback. SameflagmaskasinferenceNH_ENTITY_FUSED,butseparate. Buildv34SHA96d43249e2e9e4ab3fd648aed774cb782ae865d0992abb4db5331fb10ce369e9.

Poolbackward:pool_bwd_candidate.cuh,pool_bwd_micro.cu/.so,pool_bwd_reference_parts.cu(extractedoriginalkernels),pool_bwd_screen.py,prepare_pool_bwd.py,POOL_BWD.patch. source/ocean/nethack/pool_bwd.cuh includedafteroriginalcolsumgridhelper. NH_POOL_BWD0baseline/1specializeddv/2fuseddv+ReLU+bias,default0. TemplateactualN/PAD/OFF;64featureguard;NH_ENT_LINPOOLfallback. FusedpathretainsBF16roundbeforeReLU,samebiasgrid,threadstride,floataccumulationorder,int64fixedpointquantization. Spellbiasmemsetsmovedbeforepoolrouting(independenttensors),otherordersunchanged. Firstv35compilefailedonfrom_floatmacro/templatecommas;parenthesizingexpressionfixedv35b(noequationchange). Allheadersaddedbuildsnapshot.

## Next direction

RecentGPUforward+3% andinference+18% savedlittlefullSPS;increasedexposedtailshowsneedtofocustheCPU/rolloutcriticalpathoracombinedCPU/GPUwin. Avoidblindlyrepeatingclosedlocality/schedulerideas. PriorCPUevidence:POOL_TIMING_FULL_PHASES.json(per-bufferenv~943ms/horizon,claim~656ms,tail~286ms,readerdrain~.61ms;overlapmeansnotadditivewallshares). PRIORITY32_PROFILE.md islatestprofile;traceperturbsruntime. Existingcostorder,bufferfocus/fairness,cohorts,sleep,sharedobjects,broadprefetch,hugepages,andpackingmostlyclosed;readLEDGERandpreviouscampaignREPORTbeforechoosingnextmechanism.

Relevantengineprofileartifacts: /puffertank/experiments/nethack-compact-state-20261008/object_presence_20261009/ (REPORT.md,hotspots.json,rest_function_deltas.json,stack_samples.csv); primary_movement_costs_20261009/ andfull_gap_20261009/. CurrentretainedPGOengine movement_object_presence_pgo_followthrough. Thesehistoricalprofilesareevidence,notnewmeasurements. Needboundednewhypothesisorcurrentcriticalpathmeasurement,notanothergenericcacheguess. No newCPUcandidate implemented yet.

Harnessrun.py/campaign.py/build.py/full_summary.py/summarize.py unchangedsemantics. Fixed2048env/4buffers/H128/batch262144/mb4096/113updates.512uniqueactionsrepeated4xlimitation. Serializeheavywork,minuteupdates,stoponlyverifiedPIDs. KeepgoalACTIVE.
