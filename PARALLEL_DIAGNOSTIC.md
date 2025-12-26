# Parallel Solver Diagnostic Report

## Test Configuration
- Hardware: 8 threads available
- Strategy: Border-First + MRV + LCV

---

## FIXES APPLIED

### Fix 1: Increased Partition Depth for Border-First
**File:** `solvers/v2/parallel/parallel_solver.cpp`

Before: depth 2 for all strategies → 12 work units
After: depth 5 for border-first → 72 work units

### Fix 2: Race Condition in Solution Detection
**File:** `solvers/v2/parallel/parallel_solver.cpp`

Before: Multiple threads claim "found solution"
After: `compare_exchange_strong` ensures only first thread claims

### Fix 3: Benchmark Displays Parallel Results
**File:** `solvers/benchmark/benchmark.cpp`

Added V2P Time, P.Speedup, V2P Solved columns to table

---

## RESULTS AFTER FIXES

### Size 7 Puzzle (size_7_colors_6_c54a3b2d.csv)
| Metric | Before Fix | After Fix |
|--------|------------|-----------|
| Partition Depth | 2 | 5 |
| Work Units | 12 | 72 |
| V2 Single Time | 1913 ms | 1981 ms |
| V2 Parallel Time | ~1908 ms | 1646 ms |
| Parallel Speedup | ~1.0x | **1.2x** |

---

## REMAINING ISSUES

## Issue 1: Insufficient Work Units (FIXED)

---

## Issue 2: Same Node Count (No Search Reduction)

### Observation
```
Single-threaded: 1,354,117 nodes
Parallel:        1,354,117 nodes (same!)
```

### Root Cause
Parallel solver explores the SAME search space, just distributed across threads. It doesn't benefit from:
- Clause learning across threads
- Shared pruning information
- Work stealing from productive branches

### Impact
- Total work is identical to single-threaded
- Only benefit is wall-clock time reduction (if any)

---

## Issue 3: Race Condition in Solution Detection

### Observation
```
Thread 0 found solution with profile 0
Thread 4 found solution with profile 3
Thread 6 found solution with profile 0
Thread 1 found solution with profile 3
```

Multiple threads claim to find solution!

### Root Cause
After `solution_found_ = true` is set:
1. Other threads may already be past the check in their loop
2. They complete their work unit and also set solution_found_
3. No lock protecting the "first solution wins" logic

### Impact
- Wasted computation
- Confusing output
- Potential for solution to be overwritten

---

## Issue 4: Benchmark Doesn't Display Parallel Results

### Observation
```
V2 Time: 1872.86 ms   (this is single-threaded V2!)
```

The benchmark runs BOTH V2 single and V2 parallel, but `print_table()` only shows `v2_result`, not `v2_parallel_result`.

### Root Cause
`print_table()` function doesn't have columns for parallel results.

---

## Issue 5: Work Unit Collection Overhead

### Observation
Work units are collected SERIALLY before parallel phase begins.

### Code Location
```cpp
// Phase 1: Collect work units at partition depth (SERIAL)
std::vector<WorkUnit> work_units;
collect_work_units(work_units, target_depth);
// ... then distribute to threads
```

### Impact
For fast puzzles, collection time may exceed parallel benefit.

---

## Comparison: Single vs Parallel

| Metric | Single-threaded | Parallel | Difference |
|--------|-----------------|----------|------------|
| Time (size 9) | 62.88s | 56.92s | **1.1x** |
| Nodes | 40.66M | 40.66M | Same |
| Work units | N/A | 12 | Too few |

**Only 10% speedup despite 8 threads!**

---

## Recommendations

### High Impact Fixes

1. **Increase Partition Depth for Border-First**
   - Current: depth 2 → 12 work units
   - Proposed: depth 4-5 → 100+ work units
   - Reason: Border-first has narrow initial branching

2. **Add Work Stealing**
   - Allow idle threads to steal work from busy threads
   - Reduces impact of imbalanced work units

3. **Display Parallel Results in Benchmark**
   - Add columns to show V2 Parallel time/nodes
   - Essential for measuring actual benefit

### Medium Impact Fixes

4. **Fix Solution Detection Race**
   - Use compare-exchange for `solution_found_`
   - Only first thread should claim victory

5. **Share Pruning Information**
   - When one thread finds a conflict, share it
   - Other threads can avoid same dead-end

### Low Impact (Future)

6. **Parallel Work Unit Collection**
   - Collect work units in parallel
   - Marginal benefit for current bottleneck

---

## Conclusion

The parallel solver provides minimal speedup (1.1x) because:
1. Too few work units (12 for 8 threads)
2. Same total work (no shared learning)
3. Border-first narrows the search tree too early

**Primary fix needed: Increase partition depth when using border-first strategy.**
