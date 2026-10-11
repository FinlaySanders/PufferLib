# CUDA graph scratch-allocation limit: measured rule

Date: 2026-09-18. RTX 4090, driver 595.71.05, CUDA/cuBLAS 13.1.

## Finding

Upstream cuBLAS capture changes algorithm after a real `cudaMallocAsync` allocation failure, not simply an unexplained heuristic choice. CUPTI records both `cuMemAllocAsync` and `cudaMallocAsync` returning error 2 at capture index 1505 (zero-based). cuBLAS handles this failure and successfully captures a GEMM that needs no scratch workspace. The preceding 1505 captures use split-K and a 98,304-byte graph allocation.

A bare CUDA reproducer, with no cuBLAS, demonstrates that retained graph allocations exhaust a finite virtual-address reservation budget on this system. Physical GPU memory is not exhausted. CUDA graph allocation addresses remain reserved while the graph/executable exists; execution of its free node does not release this address reservation.

## Measurements

| Requested allocation per retained graph | Successful captures before error 2 |
|---|---:|
| 16 bytes | 1505 |
| 96 KiB | 1505 |
| 4 MiB | 1505 |
| 32 MiB | 1505 |
| 64 MiB | 752 |
| 128 MiB | 376 |

For the smaller requests, consecutive returned addresses are 32 MiB apart. These measurements fit an approximately 47 GiB usable virtual-address budget with 32 MiB allocation granularity. This is an empirical characterization of this driver/device, not a documented universal CUDA limit or a recovered driver constant.

Controls:
- Keeping uninstantiated graphs, never executing them, hits the same threshold with graph physical memory usage/reservation both zero.
- Keeping executable graphs hits the threshold with only 32 MiB physical graph memory reserved and about 23 GiB GPU memory free.
- Destroying each executable after use passes all 5000 captures.
- Destroying one retained executable at the threshold permits exactly one additional capture.
- Reserving 1 GiB or 8 GiB with ordinary cudaMalloc before capture does not change the threshold.
- Reducing process memlock limit to 1 MiB or 64 KiB does not change the threshold.

## Connection to Puffer

The training capture creates and retains enough rollout graphs to cross this limit. Earlier traces contained exactly 1505 graphs using split-K and 543 using the alternative. Capture ordering between streams varies, so different logical rollout steps get the two algorithms on different runs. Different reduction orders produce different BF16 results, even for identical inputs. Our private per-stream workspace avoids these captured scratch-allocation nodes; previous controls show that it stabilizes the kernels and restores repeatability for NetHack and Craftax.

Do not describe this as ordinary VRAM exhaustion or assert that CUDA universally has a 1505-graph limit. We isolated the allocation-failure mechanism and measured its address-budget behavior; NVIDIA's internal choice of budget remains undocumented here.

## Reproduction

Sources and binaries: pool.cu, pool_trace.cu (CUPTI callbacks), graph_alloc.cu, graph_alloc_extra.cu. Logs in this directory.

- ./pool 2500 1: retain execs, transition at 1505.
- ./pool 2500 0: destroy execs, no transition.
- ./graph_alloc 16 2: retain graphs without execution, failure at 1505.
- ./graph_alloc 67108864 2: failure at 752.
- ./graph_alloc 134217728 2: failure at 376.

Official lifetime description: https://docs.nvidia.com/cuda/archive/13.1.0/cuda-programming-guide/04-special-topics/cuda-graphs.html

No production source edits were made for this investigation.

## Exact driver calculation isolated (follow-up)

The previous uncertainty about budget sizing is now resolved for driver 595.71.05 on this device. This is more than a fit to observed thresholds: disassembly, live debugger values, a syscall trace, and interventions all agree.

The graph allocator initializes a virtual-address pool from twice CUDA-reported total device memory. Here:
- cudaMemGetInfo total = 25,249,579,008 bytes.
- Driver budget routine doubles this to 50,499,158,016 bytes.
- Address reservation rounds up to 32 MiB granularity: 50,499,420,160 bytes, exactly 1505 slots.
- gdb catches the corresponding mmap(PROT_NONE) at address 0x302000000, length 50,499,420,160, during the first graph allocation.
- 64 MiB allocations use two slots; 128 MiB use four, explaining thresholds 752 and 376.

Relevant offsets in libcuda.so.595.71.05 (internal names stripped; objdump's nearby exported-symbol labels are NOT actual function names):
- 0x27b95d calls budget helper 0x2ab2f0.
- 0x2ab576 calls device-memory helper 0x23f170, which on this path reads the device memory field at offset 0x6010.
- 0x2ab462 loads the budget; 0x2ab466 `add %rax,%rax` doubles it; 0x2ab469 stores it.
- Live breakpoint: BEFORE DOUBLE = 25,249,579,008; BUDGET RETURN = 50,499,158,016.
- The budget helper contains other hardware/configuration branches. Do not assert this formula for all NVIDIA devices/drivers.

Causal interventions (debugger changes to the diagnostic process only):
| Budget override | Predicted successful tiny graph allocations | Observed |
|---|---:|---:|
| 2 GiB | 64 | 64 |
| 128 GiB | 4096 | 4096 |

A further cuBLAS control overrides this same budget to 128 GiB and repeats 2500 retained graph captures. All remain split-K with 98,304-byte workspace; the original transition at 1505 disappears. This directly connects the driver's budget to the cuBLAS fallback.

After graph allocation failure, a separate cuMemAddressReserve of 128 GiB succeeds. Thus the failure is exhaustion of this allocator's reserved arena, not exhaustion of general process/GPU virtual addresses. Supplying maxSize in graph allocation-node properties (0, 1 GiB, 128 GiB) does not change the graph pool threshold in this driver.

Artifacts: graph_limits.cu; limits-*.log; maps.gdb/maps-gdb.log; budget.gdb/budget-gdb.log; budget-64.gdb/.log; budget-4096.gdb/.log; pool-budget.gdb/.log. No driver files or production sources were modified. Debugger overrides ended with the diagnostic processes.
