---
name: vol-124-roaming-nonpuzzle
description: "Vol-124 round 3: roam non-puzzle domains for E2 attacks. Physics (spin ice, Ising machines), electronics (FPGA SAT, photonic Ising), biology (DNA/RNA folding, protein lattice), materials (epitaxial growth, tile self-assembly). Highest EV finds: commercial Ising/QUBO solvers (Toshiba SQBM+, Fixstars Amplify AE), FPGA SAT (SAT-Accel 2025), and Codognet 2025 permutation-QUBO encodings."
metadata:
  type: session
---

# Vol-124 — non-puzzle-domain roam (physics, electronics, biology, materials)

User directive: *"wanna take a look at other potential domain (physic,
électronic, etc…)"*

Rule reminder this session (NEW, saved as
[feedback_multi_week_projects_allowed]): **multi-week projects are in
scope**. Don't pre-shrink scope.

## Domains roamed (8)

1. Spin ice / frustrated magnets (PHYSICS)
2. Toshiba SBM / SQBM+ (ELECTRONIC / COMMERCIAL)
3. DNA origami / sequence design (BIOLOGY)
4. Photonic circuit routing (ELECTRONIC / PHOTONICS)
5. FPGA SAT solvers (ELECTRONIC / HARDWARE)
6. Photonic Ising machines (ELECTRONIC / OPTICS)
7. RNA pseudoknot prediction (BIOLOGY)
8. Abstract Tile Assembly Model (Winfree, MATERIALS / CS-THEORY)
9. Crystallographic phase problem (PHYSICS)
10. QUBO permutation encodings (Codognet 2025) (CS / OR)

## Top-ranked finds

### F1. Toshiba SQBM+ on Azure Quantum — IMMEDIATELY ACCESSIBLE

**The most impactful single find.** Commercial Ising solver hosted on
Microsoft Azure Quantum. Two algorithms:
- **bSB** (ballistic Simulated Bifurcation) — fast, less accurate
- **dSB** (discrete Simulated Bifurcation) — slow, more accurate

**Scale**: up to **10M variables**, complete-graph couplings up to 100k.

**Benchmark performance**: in Oshiyama-Ohzeki Max-Cut benchmark across
45 instances, SBM was 3rd best after D-Wave Hybrid (22 wins) and
Fujitsu DA v2 (20), with SBM at 16 wins vs simulated annealing's 7.

**Fit to E2**: encode E2 as QUBO. Our SAT encoding has 167k vars × 5.8M
clauses. With efficient permutation encoding (see F10 below), we should
fit comfortably within 10M Ising spins. **Azure billing is per-minute**,
so a 1h SQBM+ run on canonical E2 is on the order of $10-100. Feasible.

### F2. Photonic Hopfield Ising machine (Nature 2025) — RESEARCH ONLY

Programmable 200 GOPS optoelectronic oscillator Ising machine. Solved
fully-connected problems up to **256 spins** (65,536 couplings) and
**41,000 spins for sparse problems**.

**Fit to E2**: 41k sparse spins is below our 167k needs but in the
ballpark. The 256-spin fully-connected case is interesting because E2's
border-ring problem is exactly 256 spins (one per border cell × rotation,
or one per pair). Not accessible publicly, but worth flagging as an
academic-collaboration target.

### F3. Fixstars Amplify AE — IMMEDIATELY ACCESSIBLE (GPU annealer)

**Cluster of GPUs running as digital annealer**. 65k bits with complete
graph couplings. **Public commercial API**. Codognet 2025 (Wiley ITOR)
used it for permutation-QUBO benchmarks. Same fit profile as Toshiba
but smaller scale.

### F4. Codognet 2025 — Permutation QUBO encodings — HIGH-EV PAPER

**Direct match for E2.** E2 is exactly a permutation problem (assign
each of 256 pieces to a cell). The paper compares **integer encodings
for permutation problems** in QUBO. This determines whether our QUBO
formulation will be efficient or wasteful.

**Action**: read Codognet 2025 (Wiley ITOR DOI:10.1111/itor.13471).
The optimal encoding may make E2-as-QUBO tractable on commercial
hardware.

### F5. SAT-Accel FPGA solver (ACM FPGA 2025) — RESEARCH-INTENSIVE

Modern SAT solver in hardware. 2.8× speedup over kissat on average,
17.9× over MiniSAT, 800× over prior FPGA SAT solvers.

**Fit to E2**: our kissat run took 1h on canonical with no decision.
**3× = 20 min decision** — IF the underlying solver could decide. If
canonical E2 is genuinely past kissat's reach, 3× doesn't help.

**Realistic**: not a primary attack. We'd need an FPGA development
kit, port our encoding to their input format, etc. Multi-week effort
with uncertain payoff. **Defer**.

### F6. Spin ice + deep learning ground state (Nature SR 2022) — TRANSFER

Deep learning for ground state of frustrated magnet. The transfer is
that **E2 is a frustrated system in the magnetic sense** — many
"locally good" partial placements that don't extend globally. The
methodology (planting solutions, denoising training) may transfer.

**Status**: defer; lower EV than F1-F4.

### F7. Winfree aTAM (Natural Computing 2025) — THEORETICAL

The Abstract Tile Assembly Model has Turing-universal computation in
2D. The recent work (UCNC 2024) is on **self-assembly of patterns** —
designing tile sets that grow into target patterns.

**Fit to E2**: inverse direction. E2 has a fixed tile set; we want
to *check* whether any 480 assembly exists. aTAM theory tells us
this is undecidable for infinite tilings but **decidable for finite
square instances** (per Tyburec 2023). Not directly an algorithm,
but a framework.

### F8. RNA pseudoknot KnotFold (Nature Comm Bio 2024) — METHODOLOGY

**Min-cost flow with learned potentials** for an NP-hard combinatorial
problem (pseudoknot prediction). The structure: learn a potential
function from data, use exact min-cost flow to solve the optimization.

**Transfer to E2**: if we had a *learned potential* over (piece, cell)
pairs from many partial-solution traces, we could solve a min-cost
flow problem to recover the global placement. The challenge is
generating training data — but we have ~150 459-basin boards in our
corpus.

**Multi-week effort, but mathematically clean.** Build a flow network
where pieces are sources, cells are sinks, edge weights are learned
from corpus. **Worth a vol.**

### F9. DNA origami constraint solver (REVNANO) — METHODOLOGY

Constraint programming for **reverse engineering** structures from
sequences. Different direction from us, but the CP solver style
might generalize.

**Status**: low EV; we already have CP solvers.

### F10. Crystallographic phase problem + deep learning (PhAI / Science 2024) — INSPIRATION

Deep neural net solves the crystallographic phase problem (a hard
inverse problem). Methodology: train on synthetic structures, predict
phases. **Transfer**: our W9 quantum-amplitude scoring tried similar
ideas. The PhAI result suggests it CAN work on hard inverse problems
if training data is generated synthetically.

**Status**: inspiration only; W9 is a partial attempt at this.

## Action items

**IMMEDIATE (vol-125+, cheap to try)**:
1. **W15 — QUBO encoding of E2 + SQBM+ trial on Azure.** Build a QUBO
   formulation (with Codognet 2025 best permutation encoding), submit
   to Azure Quantum SQBM+ via API. Cost: $10-100 for a 1h run.
   Compare result to kissat 1h.
2. **W16 — Read Codognet 2025 carefully**, pick the permutation
   encoding (one-hot, integer, sorting-network, domain-wall, unary),
   compare bit-counts and constraint complexity for canonical E2.

**MEDIUM (vol-126+, days of work)**:
3. **W17 — Min-cost flow with learned potentials** (KnotFold-style).
   Build a flow graph from corpus. Learn edge potentials. Run min-cost
   flow. Verify resulting assignment.

**SPECULATIVE (multi-week, autonomous-OK per new rule)**:
4. **W18 — FPGA SAT** if a collaboration / hardware lease can be
   arranged. Not a primary attack but a force-multiplier if other
   attacks plateau at 3×-of-decision.

## Refuted / out-of-scope from this roam

- **Spin ice deep learning** — applicable but transfer unclear; lower
  EV than direct QUBO encoding.
- **DNA origami** — wrong direction (we have CP).
- **Photonic Hopfield** — not publicly accessible.
- **RNA pseudoknot** — methodology transfer in F8 above; primary
  algorithm doesn't directly apply.

## Sources

### Ising / QUBO machines
- Toshiba SQBM+ Azure Quantum: azure.microsoft.com/en-us/blog/quantum/2022/06/27/toshiba-launches-new-sqbm-quantum-inspired-optimization-provider-on-azure-quantum
- Toshiba SBM Max-Cut benchmark (arxiv 2507.22117)
- Fixstars Amplify AE: codognet 2025 (Wiley ITOR doi:10.1111/itor.13471)
- Photonic Hopfield Ising (Nature 2025): nature.com/articles/s41586-025-09838-7

### Permutation QUBO encodings
- Codognet 2025 (Wiley ITOR): onlinelibrary.wiley.com/doi/10.1111/itor.13471
- Penalty weights for permutation QUBO (arxiv 2206.11040)
- Succinct QUBO via sorting networks (arxiv 2603.07579)

### FPGA SAT
- SAT-Accel (ACM FPGA 2025): dl.acm.org/doi/10.1145/3706628.3708869
- FYalSAT (FPGA stochastic local search, 2024)
- BCP-on-FPGA (arxiv 2401.07429)

### Biology methodology transfers
- KnotFold (Nature Comm Bio 2024): nature.com/articles/s42003-024-05952-w
- PhAI crystal phase (Science 2024): science.org/doi/10.1126/science.adn2777
- HP-model protein folding NP-completeness (Berger 1998)

### Materials / tile theory
- Tyburec-Zeman bounded Wang tilings (arxiv 2205.02295)
- Winfree aTAM (Natural Computing 2025, springer doi:10.1007/s11047-025-10035-8)
- Wang tile decidability via chaotic mapping (arxiv 2507.13268)

### Frustrated magnetism transfer
- Spin ice deep learning ground state (Nature SR 2022): nature.com/articles/s41598-022-19312-3
- D-Wave 3D Ising spin glass (PRX 2025): arxiv.org/abs/2501.01107
