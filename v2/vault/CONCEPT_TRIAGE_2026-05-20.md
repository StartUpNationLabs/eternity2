---
tags: [audit, meta]
date: 2026-05-20
vol: 188
---

# Concept Triage (vol-188 close)

344 concept pages, after a subagent triage pass.

## Coverage statistics

- 344 pages total.
- **56 have explicit `status:` frontmatter (16%).** 288 do not.
- 37 of 56 labeled = `built` variants; 15 = `refuted/partial`; 10 = `unbuilt/open`.

## Cluster verdicts

| Prefix | Count | Verdict | Umbrella created? |
|---|---:|---|---|
| `vol122-*` | 19 | mostly built/documented | [[concepts/_umbrella-vol122-experiments]] |
| `j1-*` | 18 | bounded at band-12/14 wall; succeeded by V155+V181 | [[concepts/_umbrella-j1-builder-attempts]] |
| `mcgavin-*` | 18 | strong (MIP rigidity proofs through halo-4) | [[concepts/_umbrella-mcgavin-mip-proofs]] |
| `cas-*` | 9 | refuted as greedy approach | [[concepts/_umbrella-cas]] |
| `sigma-*` | 9 | core theory (indecomposability); see [[concepts/sigma-cycle-universal-indecomposable]] | (existing pages stand) |
| `basin-*` | 7 | varied; [[concepts/corner-permutation-study]] is the live one | (no umbrella needed) |
| `blackwood-*` | 6 | mixed; [[concepts/blackwood-algorithm]] is canonical | (no umbrella needed) |
| `v125-*` | 6 | 461 reproducibility cluster; vol-125 session covers | (no umbrella needed) |
| `local459-*` | 5 | per-cut MIP proofs of local-459 rigidity | covered by [[PAPER_2026-05-16_canonical_E2_rigidity_theorem]] |

## Duplication and stub findings

### Confirmed mergeable

- `cas-frame-variance` (1.1 KB) is a precursor to `cas-frame-final` (1.6 KB). Both stand under no-quiet-deletes; umbrella notes the precursor relation.
- `mcgavin-top3-mip-locked` ≈ `mcgavin-top3-mip-proven` (same result, slightly different language).

### Aged unbuilt pages — vol-15-34 origin

Most are CSP reference material (AC-family, alldiff-regin, compact-table). The active CSP stack uses GAC-color + AC-3 (vol-1 baseline). The other variants are reference pages we never built, kept for the record.

| Page | Origin | Decision |
|---|---|---|
| `alldiff-regin.md` | vol-15 | KEEP as reference; we use Régin's idea (GAC-color is the spec) |
| `compact-table.md` | vol-17 | mark `wont-do` (modern CSP literature; not E2-relevant under current bound walls) |
| `ac4.md` | vol-16 | KEEP as reference; original notes mark "skip" |
| `ac2001.md` | vol-16 | KEEP as reference |
| `gac-schema.md` | vol-16 | KEEP as reference |
| `ac6.md`, `ac7.md` | vol-16 | KEEP as reference |
| `fitness-landscape-mapping.md` | vol-34 | DEFER — interesting but low EV vs current basin/record work |

These are kept under the "no quiet deletes" rule; they're light enough to leave.

## Session-note pages that escaped into concepts/

5 strict-pattern session notes (`vol##-finding`):
- `vol121-458-corner-perm-2310.md`
- `vol22-471-bound-reinterpretation.md`
- `vol32-458-halo3-proven.md`
- `vol122-25-edge-gap-is-all-interior.md` (folded into the vol122 umbrella)
- `vol122-sigma-perm0-444-to-mcgavin-indecomposable.md` (folded into the vol122 umbrella)

**Decision**: leave them. They each document one concrete finding and have stable wikilink targets.

## Action items (this pass)

1. [x] Create 4 umbrella pages: vol122, j1, mcgavin, cas. Done above.
2. [ ] (future) Add explicit `status:` frontmatter to the ~288 unlabeled pages. Out of scope for vol-188 synthesis; would take ~3-4 hours.
3. [ ] (future) Consolidate `mcgavin-top3-mip-locked` and `mcgavin-top3-mip-proven`. Leave both for now.
4. [ ] (future) Promote `local459-*` titles like "proven" to explicit `status: built`.

## Why the umbrellas matter

The vault is read by humans (Obsidian) and agents (next-vol Claude). 344 concept pages is too many to skim. Umbrellas like `_umbrella-vol122-experiments` show up alphabetically at the top of `concepts/` and give a one-page entry into a 19-page sub-cluster. A future agent looking for "what did vol-122 build?" finds the umbrella first.

The `_` prefix sorts them ahead of all concept files in Obsidian; intentional.

## Linked

- [[AUDIT_2026-05-20]] — the audit that triggered this triage
- [[SYNTHESIS_VOL_188]] — the master synthesis
- [[INDEX]] — vault MOC
