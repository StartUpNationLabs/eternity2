//
// Variable Ordering Heuristics for solver_v2
// Implements MRV (Minimum Remaining Values) with Degree tie-breaker
//

#ifndef ETERNITY2_V2_VARIABLE_ORDERING_H
#define ETERNITY2_V2_VARIABLE_ORDERING_H

#include "../constraints/domain.h"
#include <limits>
#include <optional>

namespace eternity2_v2 {

// Result of variable selection
struct VariableSelection {
    Index index;
    size_t domain_size;
    size_t degree;
    bool is_failure;  // True if any domain is empty
};

// Select next variable using MRV heuristic with degree tie-breaker
// Returns nullopt if all variables are assigned (solution found)
// Sets is_failure=true if any domain is empty (dead end)
VariableSelection select_variable_mrv(const DomainManager& domain_manager);

// Simple MRV without degree tie-breaker (for comparison)
VariableSelection select_variable_mrv_simple(const DomainManager& domain_manager);

// Static ordering (for comparison with v1 - spiral-like)
VariableSelection select_variable_static(const DomainManager& domain_manager);

// Select variable with most unassigned neighbors (fail-last, for comparison)
VariableSelection select_variable_degree_only(const DomainManager& domain_manager);

} // namespace eternity2_v2

#endif // ETERNITY2_V2_VARIABLE_ORDERING_H
