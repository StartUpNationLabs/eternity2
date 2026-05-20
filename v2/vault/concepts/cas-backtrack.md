---
name: cas-backtrack
description: Vol-74 CAS greedy commits each shell as it's solved. Shells 3-7
status: unbuilt
metadata:
  type: concept
---
# CAS-BACKTRACK — vol-78 design (2026-05-15)

**Status**: `design` — vol-78.
**Type**: VARIANT of CAS (vol-74), adding tree-search.

## Why

Vol-74 CAS greedy commits each shell as it's solved. Shells 3-7
progressively fail (71/72, 53/56, 34/40, 16/24, 4/8 matched).
Vol-76 confirmed: across 20 different frames, CAS plateaus at
430-436. The variance is small — frame choice doesn't fix the
greedy-commit problem.

CAS-BACKTRACK adds: when a shell completes with mismatches, BACKTRACK
to the previous shell and try a different solution (using the
cutting-plane technique from vol-76 frame enumeration).

## Algorithm

```
def CAS_BACKTRACK(max_attempts_per_shell=5):
    placement = {}  # shell 0 onwards
    shell_attempts = [0] * 8  # number of attempts so far at each shell
    shell_forbidden = [[] for _ in range(8)]  # forbidden solutions

    shell = 0
    while shell < 8:
        # Try to solve shell with current forbidden list
        new_placement, shell_score = solve_shell_with_cuts(
            shell, placement, shell_forbidden[shell]
        )
        if shell_score == max_possible(shell):
            # Perfect shell; commit and move to next
            placement.update(new_placement)
            shell += 1
        elif shell_attempts[shell] < max_attempts_per_shell:
            # Imperfect shell. Forbid this solution + try again.
            shell_forbidden[shell].append(extract_solution_signature(new_placement))
            shell_attempts[shell] += 1
            # Don't update placement; loop and retry
        else:
            # Exhausted attempts; BACKTRACK
            if shell == 0:
                # Can't go back further; commit best-so-far
                placement.update(new_placement)
                break
            shell -= 1
            shell_forbidden[shell].append(extract_solution_signature(placement))
            shell_attempts[shell] += 1
            placement = remove_shell(placement, shell)
            shell_attempts[shell + 1] = 0
            shell_forbidden[shell + 1] = []
    return placement
```

## Properties

- **Depth-limited**: each shell tries up to `max_attempts_per_shell`
  before backtracking.
- **Exponential worst case** in `max_attempts_per_shell^8`, but
  with good initial frames, may converge quickly.
- **Sound**: each shell's MIP is exact within its budget.

## Variants

- **CAS-BACKTRACK-PARTIAL**: at each shell, ACCEPT a near-perfect
  solution (e.g., 1 missing edge) and continue; only backtrack on
  major failures.
- **CAS-BACKTRACK-RANDOM**: instead of cutting-plane to forbid a
  specific solution, just re-solve with random seed.
- **CAS-BACKTRACK-CHAIN**: backtrack from current shell ALL THE
  WAY to shell 0 if a deep shell fails, then try a new frame.

## Build complexity

- Reuse vol-74 cas_full_fixed's shell solver.
- Add cutting-plane cut for the previous shell's solution.
- Stack management for backtracking.

## Expected behavior

- If CAS plateau is at shells 6-7 (deep center), backtracking from
  shell 7 to shell 5 or 4 should help.
- If CAS plateau is structural (no path through any frame leads
  to high score), backtrack converges back to ~430-440 anyway.

Vol-78 will test this.

## Linked

- vault/concepts/concentric-annular-solving.md (parent)
- vault/concepts/cas-greedy-433-result.md
- vault/concepts/cas-frame-variance.md
