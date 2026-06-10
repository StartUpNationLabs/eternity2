# Current Volume — Vol-211 (draft) — strategic inflection after the entropy track

**Status**: drafted at vol-210 close. The clever/structural attack space is now
thoroughly mapped and exhausted; this vol is a DECISION point, not a build (yet).

## Where we are (verified across vols 203-210 + this session's deep dives)
- Local search, ALNS, all from-scratch constructors: ~460 ceiling (exhausted).
- The sub-480 bound: doesn't exist (480 is achievable; vol-208).
- Strip/assignment decomposition: no selective objective (refuted, vol-208).
- Scarcity value-ordering: weak/backtrack-neutral (3× confirmed).
- ISENTROPE entropy characterization (vol-209): SOLID — grammar entropy density
  h∞≈0.67>0; distinctness AREA-LAW ρ≈exp(−0.085 n²) collapses at ~80 cells = the wall;
  interior grammar-uniform (95.5%). The hardness IS the global distinctness layer.
- Conditional marginals (vol-210): χ-truncation artifact, NOT usable (refuted-as-tool).
- **Blackwood (community's 469 method) re-examined (vol-210)**: the project has #1
  schedule + #2 breaks + #4 speed (85M nps) but NOT #3 (McGavin/Joe prune-back-to-T
  with no-good learning on the fast engine). HOWEVER — throughput arithmetic: Blackwood
  reached 469 with ~295M nps × 200 cores × ~30 days ≈ 10²¹ node-attempts. This machine:
  85M nps × 8 cores × 5 days ≈ 10¹⁴ — **~10⁶-10⁷× fewer**. Even with prune-back (2×),
  the gap is 6 orders of magnitude. **One machine is throughput-doomed for Blackwood's
  brute-force-with-breaks; building #3 + running long will NOT reach 469.** (Corrects
  the vault's "structural wall" — it's a throughput wall, not structural.)

## The honest conclusion (the inflection)
Every single-machine route — clever (structural/entropy/decomposition) AND brute
(Blackwood-grade backtracking) — is now either refuted or shown to be ~10⁶× under-
resourced. **A canonical-5-clue record (>463) or solution (480) is not reachable on
this one machine** by any known method. The proven path (community 469) is fundamentally
distributed-exact at a scale (200 cores × weeks) this machine cannot emulate.

## Options for vol-211 (DECISION REQUIRED — not autonomous-buildable)
1. **Accept the characterization as the deliverable.** vols 203-210 produced a
   rigorous, quantified theory of WHY E2 is hard (area-law of distinctness) + several
   validated tools (MPS contractor, entropy counter). Write the synthesis paper; stop
   chasing a single-machine record. [Highest intellectual honesty.]
2. **Cloud / distributed.** The ONLY path to ≥469 is distributed-exact. If cloud compute
   becomes available, build the best Blackwood+prune-back and run it at 100+ cores ×
   weeks. [The only real record path — needs resources beyond this machine.]
3. **A genuinely orthogonal reframe not yet conceived.** 210 vols have been thorough;
   the probability of an unconsidered single-machine angle with real upside is low, but
   not zero. Keep it on the table only if a concrete new idea appears.

## Recommendation
Option 1 (synthesize + stop single-machine record-chasing) is the honest call, with
Option 2 (distributed) as the real record path if resources allow. Do NOT start another
single-machine record attempt — the evidence against it is now overwhelming and
multi-angle. Await user direction.

## Linked
- [[tidemark-conditional-marginals]], [[isentrope-entropy-growth]],
  [[MATH_NOTES_2026-06-10_isentrope_entropy_theorem]], [[blackwood-algorithm]],
  [[prune-restart]], [[mcgavin-blackwood-gap-analysis]] (if exists), [[SYNTHESIS_VOL_207_2026-06-10]].
