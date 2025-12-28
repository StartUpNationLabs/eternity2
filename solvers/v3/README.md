# Solver V3 - Dancing Links Implementation

## Status: IMPLEMENTED (Needs Optimization)

V3 implements Knuth's Algorithm X with Dancing Links (DLX) for exact cover problem solving. However, performance improvements over v2 are limited. This document outlines research findings and optimization opportunities.

## Current Implementation

### What V3 Has

- ✅ Basic DLX with S-heuristic (minimum column size)
- ✅ Edge compatibility checking during search
- ✅ Border-first column selection heuristic
- ✅ LCV (Least Constraining Value) row ordering
- ✅ Constraint propagation (cascade propagation for singletons)
- ✅ Parallel portfolio search with multiple heuristic profiles
- ✅ Memory-efficient matrix structure with shared metadata
- ✅ **Randomization support** for path diversification
  - Random seed configuration (thread-specific in parallel mode)
  - Random tie-breaking in column selection
  - Partial randomization in row ordering (shuffle within LCV buckets)

### What V3 Lacks (Compared to V2)

- ❌ **Full MAC (Maintaining Arc Consistency)** - V2's domain manager provides comprehensive constraint propagation
- ❌ **Degree heuristic tie-breaker** - V2 uses degree (unassigned neighbors) as secondary heuristic
- ❌ **Advanced lookahead** - V2's MAC provides deeper constraint propagation
- ❌ **Optimized domain filtering** - V2's trailing system is more efficient for backtracking
 
## Research: DLX Optimizations for Large Puzzles

### 1. Column Selection Heuristics

**Current:** V3 uses S-heuristic (minimum column size) and border-first variants.

**Research Findings:**
- **S-heuristic is standard** but can be improved with secondary heuristics
- **Degree heuristic** (count of unassigned neighbors) as tie-breaker significantly improves performance
- **Lookahead heuristics** that consider future constraint propagation can reduce search space
- **Problem-specific heuristics** (border-first, corner-heavy) are effective for spatial puzzles

**Recommendation:** Implement degree heuristic as tie-breaker when multiple columns have the same size.

### 2. Constraint Propagation

**Current:** V3 uses edge propagation with cascade for singletons.

**Research Findings:**
- **Full MAC (Arc Consistency)** provides stronger pruning than basic propagation
- **Forward checking** can detect dead ends earlier
- **Singleton propagation** (cascade) is effective but can be extended
- **Incremental constraint checking** avoids redundant work

**Recommendation:** 
- Integrate v2's domain manager concepts into DLX framework
- Implement lookahead that checks if placing a row would cause domain wipeouts
- Add constraint propagation that removes incompatible rows before recursion

### 3. Row Ordering (Value Selection)

**Current:** V3 uses LCV (Least Constraining Value) based on color frequency.

**Research Findings:**
- **LCV is effective** but can be improved with dynamic scoring
- **Dynamic LCV** that considers current board state outperforms static scoring
- **Degree-based ordering** (prefer rows that constrain fewer neighbors) helps
- **Fail-first diversification** (reverse LCV) can help in parallel search

**Recommendation:**
- Compute LCV dynamically based on current neighbor constraints
- Add degree-based scoring (rows that affect fewer unassigned positions are better)
- Consider constraint propagation cost in row ordering

### 4. Memory and Data Structure Optimizations

**Current:** V3 uses contiguous node storage and shared metadata.

**Research Findings:**
- **Contiguous memory** improves cache locality (already implemented)
- **Node pooling** can reduce allocation overhead
- **Lazy evaluation** of constraints can save computation
- **Compressed representations** for sparse matrices

**Recommendation:**
- Profile memory allocations and consider node pooling
- Cache frequently accessed metadata (position types, color frequencies)
- Consider lazy constraint checking for non-critical paths

### 5. Parallel Search Strategies

**Current:** V3 supports parallel portfolio search with different heuristic profiles.

**Research Findings:**
- **Portfolio search** is effective when profiles are diverse
- **Work stealing** can improve load balancing
- **Early termination** when one thread finds solution is critical
- **Shared read-only data** (row metadata) reduces memory overhead (already implemented)

**Recommendation:**
- Ensure heuristic profiles are sufficiently diverse
- Consider work-stealing queue for better load balancing
- Optimize early termination signaling

## Specific Improvements from V2 to Integrate

### 1. Domain Manager Concepts

V2's `DomainManager` provides:
- **Incremental domain updates** with trailing system
- **Efficient backtracking** via trail entries
- **Neighbor degree tracking** for MRV+degree heuristic
- **Color frequency analysis** for LCV

**Integration Strategy:**
- Adapt domain manager's constraint propagation to DLX row filtering
- Use degree tracking for column selection tie-breaking
- Leverage color frequency for dynamic LCV scoring

### 2. MRV + Degree Heuristic

V2's variable selection:
```cpp
// Select variable with minimum remaining values (MRV)
// Tie-break with degree (unassigned neighbors)
VariableSelection select_variable_mrv(const DomainManager& domain_manager);
```

**DLX Equivalent:**
- Column selection already uses MRV (S-heuristic = minimum column size)
- **Add degree tie-breaker:** When multiple columns have same size, prefer position columns with more unassigned neighbors
- Track unassigned neighbor count for each position column

### 3. Dynamic LCV

V2 computes LCV dynamically:
```cpp
// Calculate how constraining a piece placement would be
size_t calculate_constrainedness(
    const DomainManager& domain_manager,
    Index index,
    const RotatedPiece& piece);
```

**DLX Equivalent:**
- Current LCV uses static color frequency
- **Enhance with dynamic scoring:** Count how many rows remain in neighbor position columns after placing this row
- Consider both color frequency AND current constraint state

### 4. Border-First Strategy

V2's border-first strategy:
```cpp
// Prioritize corners, then edges, then interior
// Within each category, use MRV with degree tie-breaker
VariableSelection select_variable_border_first(const DomainManager& domain_manager);
```

**DLX Equivalent:**
- Already implemented in `choose_column_smart()`
- **Enhancement:** Add degree tie-breaker within each category (corner/edge/interior)

## Randomization for Path Diversification

V3 supports randomization to explore different search paths, which is especially useful for:
- **Parallel search**: Different threads explore different parts of the search space
- **Avoiding local minima**: Randomization helps escape stuck search paths
- **Portfolio diversity**: Different heuristic profiles with randomization create more diverse searches

### Configuration

Randomization is controlled via `SolverConfig`:

```cpp
struct SolverConfig {
    uint32_t random_seed = 0;           // 0 = time-based (each thread gets unique seed)
    float randomization_strength = 0.3f; // 0.0 = deterministic, 1.0 = fully random (default: 0.3)
};
```

**Note:** Randomization is **enabled by default** with `randomization_strength = 0.3` (light randomization). To disable, set `randomization_strength = 0.0f`.

### Randomization Features

1. **Random Seed**:
   - `0` (default): Each solver instance gets a unique time-based seed
   - In parallel mode: Each thread gets `base_seed + thread_id * 1000000` for diversification
   - Non-zero seed: All solvers use the same base seed (useful for reproducibility)

2. **Column Selection Randomization**:
   - When `randomization_strength > 0`, columns with the same score/size are randomly selected
   - Applied to both S-heuristic and border-first column selection
   - Helps break ties when multiple columns are equally good

3. **Row Ordering Randomization**:
   - **Full randomization** (`randomization_strength = 1.0`): Complete random shuffle (used by `BORDER_FIRST_RANDOM` profile)
   - **Partial randomization** (`0.0 < randomization_strength < 1.0`): Shuffle rows within LCV score buckets
     - Rows with similar LCV scores are grouped into buckets
     - Bucket size is proportional to `randomization_strength`
     - Rows within each bucket are randomly shuffled
     - Preserves LCV ordering while adding diversity

### Usage Examples

```cpp
// Default: Light randomization enabled (randomization_strength = 0.3)
SolverConfig config;  // Already has randomization enabled

// Disable randomization (fully deterministic)
config.randomization_strength = 0.0f;

// Adjust randomization strength
config.randomization_strength = 0.5f;  // Medium randomization
config.randomization_strength = 1.0f;  // Full randomization (complete random shuffle)

// Set custom seed for reproducibility (randomization still enabled)
config.random_seed = 12345;  // All runs with this seed will be identical

// Disable randomization and use fixed seed
config.randomization_strength = 0.0f;
config.random_seed = 12345;  // Fully deterministic and reproducible
```

### Parallel Search with Randomization

In parallel mode, each worker thread automatically gets a unique seed:
- Thread 0: `base_seed + 0 * 1000000`
- Thread 1: `base_seed + 1 * 1000000`
- Thread 2: `base_seed + 2 * 1000000`
- etc.

This ensures each thread explores different paths even with the same heuristic profile.

## Implementation Roadmap

### Phase 1: Quick Wins (High Impact, Low Effort)
1. ✅ Add degree heuristic as tie-breaker for column selection
2. ✅ Enhance LCV with dynamic neighbor constraint counting
3. ✅ Improve constraint propagation to detect dead ends earlier
4. ✅ **Add randomization support for path diversification**

### Phase 2: Medium-Term (Moderate Impact, Moderate Effort)
1. Integrate domain manager concepts for stronger constraint propagation
2. Implement lookahead that checks future domain wipeouts
3. Add caching for frequently computed heuristics

### Phase 3: Long-Term (High Impact, High Effort)
1. Redesign constraint propagation to match v2's MAC strength
2. Implement advanced lookahead techniques
3. Optimize memory layout for better cache performance

## Eternity II as Exact Cover

- **Rows:** (piece P, position (x,y), rotation R) tuples
- **Columns:**
  - Piece P is used (256 columns for 16x16 board)
  - Position (x,y) is filled (256 columns)
  - Edge constraints handled via row filtering (not separate columns)

## Profiling

To identify performance bottlenecks and hotpaths in the v3 solver, use the profiling script:

```bash
# Basic profiling (auto-detects best method for your platform)
./solvers/v3/profile.sh data/puzzles/puzzle.csv

# Profile for 60 seconds
./solvers/v3/profile.sh -d 60 data/puzzles/puzzle.csv

# Use specific profiling method
./solvers/v3/profile.sh -m sample data/puzzles/puzzle.csv  # macOS sample
./solvers/v3/profile.sh -m perf data/puzzles/puzzle.csv    # Linux perf
./solvers/v3/profile.sh -m gprof data/puzzles/puzzle.csv   # gprof (GCC only)

# Specify output directory
./solvers/v3/profile.sh -o ./my_profiles data/puzzles/puzzle.csv
```

### Available Profiling Methods

- **auto** (default): Automatically selects the best available method for your platform
- **sample** (macOS): Uses macOS `sample` command for time-based profiling
- **perf** (Linux): Uses Linux `perf` tool for detailed performance analysis
- **gprof** (GCC): Uses gprof for call graph profiling (requires GCC with -pg flag)
- **instruments** (macOS): Uses Xcode Instruments for GUI-based profiling

### Manual Profiling

You can also build with the Profile configuration manually:

```bash
cd build
cmake -DCMAKE_BUILD_TYPE=Profile ..
cmake --build . --target SolverV3

# Then run with your preferred profiler
sample ./solvers/v3/SolverV3 30 -f profile.txt
# or
perf record -g -- ./solvers/v3/SolverV3 data/puzzles/puzzle.csv
perf report
```

### Interpreting Results

The profiling output will show:
- **Hot functions**: Functions that consume the most CPU time
- **Call graphs**: Function call relationships and time spent in each
- **Call counts**: How many times each function is called

#### Understanding Sample Output (macOS)

The `sample` command produces a call graph showing where time is spent. Example output:

```
Call graph:
    811 Thread_22405123   DispatchQueue_1: com.apple.main-thread  (serial)
      811 start  (in dyld) + 7184  [0x197245d54]
        811 main  (in SolverV3) + 1744  [0x102e3738c]  main.cpp:306
          811 execute_solver(...)  (in SolverV3) + 728  [0x102e35b08]  main.cpp:180
            811 eternity2_v3::DLXSolver::solve()  (in SolverV3) + 112  [0x102e3f4a8]  dlx_solver.cpp:54
              811 eternity2_v3::DLXSolver::search(unsigned long)  (in SolverV3) + 888  [0x102e3f8d0]  dlx_solver.cpp:207
                811 eternity2_v3::DLXSolver::search(unsigned long)  (in SolverV3) + 888  [0x102e3f8d0]  dlx_solver.cpp:207
```

**Key insights:**
- The number (811) represents the number of samples where this function was on the stack
- **Hotpaths** are functions with high sample counts - in this example, `DLXSolver::search()` is the hotpath
- Recursive functions (like `search()` calling itself) will appear multiple times in the call stack
- Functions deeper in the stack that appear frequently are prime optimization targets

#### What to Look For

1. **Hotpaths (High CPU time)**:
   - Functions with the highest sample counts are your primary optimization targets
   - In DLX solvers, `search()` is typically the hotpath - optimize column selection, row ordering, and constraint checking within it

2. **Frequently Called Functions**:
   - Functions called many times (even if individually fast) can accumulate significant overhead
   - Consider inlining small, frequently called functions
   - Cache expensive computations that are called repeatedly

3. **Deep Recursion**:
   - Deep call stacks indicate recursive algorithms (expected in DLX)
   - Look for opportunities to optimize the base case or reduce recursion depth
   - Consider iterative alternatives for tail-recursive patterns

4. **Memory Operations**:
   - Functions that allocate/deallocate frequently (if visible in profile)
   - Consider object pooling or pre-allocation for hotpaths

#### Typical V3 Hotpaths

Based on profiling, common hotpaths in the v3 solver include:

- **`DLXSolver::search()`**: Main recursive search function - optimize column selection and row ordering here
- **`DLXMatrix::choose_column()`**: Column selection heuristic - critical for search efficiency
- **`DLXMatrix::cover()` / `uncover()`**: Dancing Links operations - should be O(1) but verify
- **Edge compatibility checking**: Constraint propagation during search
- **Row ordering (LCV)**: Value selection heuristic

#### Viewing Full Profile Reports

The script saves complete profile reports in the output directory. To view the full report:

```bash
# View the full profile report
cat profiles/profile_<puzzle_name>_<timestamp>.txt

# Or open in your editor
code profiles/profile_<puzzle_name>_<timestamp>.txt
```

The full report includes:
- Complete call graph with all functions
- Function-level statistics
- Memory usage information
- Thread information (for parallel runs)

#### Optimization Strategy

1. **Profile first**: Always profile before optimizing to identify actual bottlenecks
2. **Focus on hotpaths**: Optimize the top 2-3 functions that consume the most time
3. **Measure impact**: Re-profile after changes to verify improvements
4. **Avoid premature optimization**: Don't optimize functions that don't appear in the profile

#### Example Workflow

```bash
# 1. Profile the solver
./solvers/v3/profile.sh -d 60 data/puzzles/puzzle.csv

# 2. Analyze the output to identify hotpaths
cat profiles/profile_*.txt | grep -A 5 "DLXSolver::search"

# 3. Make optimizations based on findings

# 4. Re-profile to measure improvement
./solvers/v3/profile.sh -d 60 data/puzzles/puzzle.csv

# 5. Compare results
diff profiles/profile_*.txt
```

## Resources

### Academic Papers
- [Dancing Links (Knuth, 2000)](https://arxiv.org/abs/cs/0011047) - Original DLX paper
- [Algorithm X (Wikipedia)](https://en.wikipedia.org/wiki/Knuth's_Algorithm_X)

### Implementation References
- [Algorithm X in 30 lines](https://www.cs.mcgill.ca/~aassaf9/python/algorithm_x.html) - Simple Python implementation
- [DLXSolver 2.0](https://www.tgmdev.be/applications/dlxsolver/dlxsolver.php) - Sudoku solver using DLX

### Related Techniques
- [Maintaining Arc Consistency (MAC)](https://en.wikipedia.org/wiki/Arc_consistency) - Used in v2
- [MRV and Degree Heuristics](https://en.wikipedia.org/wiki/Minimum_remaining_values) - CSP heuristics
- [LCV Heuristic](https://en.wikipedia.org/wiki/Least_constraining_value) - Value ordering
