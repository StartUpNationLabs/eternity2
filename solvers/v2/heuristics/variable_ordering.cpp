//
// Variable Ordering Heuristics Implementation
// MRV (Minimum Remaining Values) with Degree tie-breaker
//

#include "variable_ordering.h"

namespace eternity2_v2 {

VariableSelection select_variable_mrv(const DomainManager& domain_manager) {
    VariableSelection result;
    result.domain_size = std::numeric_limits<size_t>::max();
    result.degree = 0;
    result.is_failure = false;
    result.index = {0, 0};

    bool found_unassigned = false;

    for (size_t y = 0; y < domain_manager.board_size(); ++y) {
        for (size_t x = 0; x < domain_manager.board_size(); ++x) {
            Index index = {x, y};
            const DomainEntry& domain = domain_manager.get_domain(index);

            // Skip assigned positions
            if (domain.is_assigned) continue;

            found_unassigned = true;

            // Check for empty domain (failure)
            if (domain.empty()) {
                result.is_failure = true;
                result.index = index;
                result.domain_size = 0;
                return result;
            }

            size_t domain_size = domain.size();
            size_t degree = domain_manager.count_unassigned_neighbors(index);

            // MRV: prefer smaller domains
            // Degree: prefer higher degree as tie-breaker
            if (domain_size < result.domain_size ||
                (domain_size == result.domain_size && degree > result.degree)) {
                result.index = index;
                result.domain_size = domain_size;
                result.degree = degree;
            }
        }
    }

    // If no unassigned found, solution is complete
    if (!found_unassigned) {
        result.domain_size = 0;
        result.is_failure = false;  // Not a failure, just complete
    }

    return result;
}

VariableSelection select_variable_mrv_simple(const DomainManager& domain_manager) {
    VariableSelection result;
    result.domain_size = std::numeric_limits<size_t>::max();
    result.degree = 0;
    result.is_failure = false;
    result.index = {0, 0};

    bool found_unassigned = false;

    for (size_t y = 0; y < domain_manager.board_size(); ++y) {
        for (size_t x = 0; x < domain_manager.board_size(); ++x) {
            Index index = {x, y};
            const DomainEntry& domain = domain_manager.get_domain(index);

            if (domain.is_assigned) continue;

            found_unassigned = true;

            if (domain.empty()) {
                result.is_failure = true;
                result.index = index;
                result.domain_size = 0;
                return result;
            }

            size_t domain_size = domain.size();

            // Only MRV, no tie-breaker
            if (domain_size < result.domain_size) {
                result.index = index;
                result.domain_size = domain_size;
                result.degree = domain_manager.count_unassigned_neighbors(index);
            }
        }
    }

    if (!found_unassigned) {
        result.domain_size = 0;
        result.is_failure = false;
    }

    return result;
}

VariableSelection select_variable_static(const DomainManager& domain_manager) {
    VariableSelection result;
    result.domain_size = std::numeric_limits<size_t>::max();
    result.degree = 0;
    result.is_failure = false;
    result.index = {0, 0};

    // Simple row-by-row traversal (like static ordering)
    for (size_t y = 0; y < domain_manager.board_size(); ++y) {
        for (size_t x = 0; x < domain_manager.board_size(); ++x) {
            Index index = {x, y};
            const DomainEntry& domain = domain_manager.get_domain(index);

            if (domain.is_assigned) continue;

            if (domain.empty()) {
                result.is_failure = true;
                result.index = index;
                result.domain_size = 0;
                return result;
            }

            // Return first unassigned (static ordering)
            result.index = index;
            result.domain_size = domain.size();
            result.degree = domain_manager.count_unassigned_neighbors(index);
            return result;
        }
    }

    // All assigned
    result.domain_size = 0;
    result.is_failure = false;
    return result;
}

VariableSelection select_variable_degree_only(const DomainManager& domain_manager) {
    VariableSelection result;
    result.domain_size = std::numeric_limits<size_t>::max();
    result.degree = 0;
    result.is_failure = false;
    result.index = {0, 0};

    bool found_unassigned = false;

    for (size_t y = 0; y < domain_manager.board_size(); ++y) {
        for (size_t x = 0; x < domain_manager.board_size(); ++x) {
            Index index = {x, y};
            const DomainEntry& domain = domain_manager.get_domain(index);

            if (domain.is_assigned) continue;

            found_unassigned = true;

            if (domain.empty()) {
                result.is_failure = true;
                result.index = index;
                result.domain_size = 0;
                return result;
            }

            size_t degree = domain_manager.count_unassigned_neighbors(index);

            // Only degree heuristic (fail-last approach)
            if (degree > result.degree) {
                result.index = index;
                result.domain_size = domain.size();
                result.degree = degree;
            }
        }
    }

    if (!found_unassigned) {
        result.domain_size = 0;
        result.is_failure = false;
    }

    return result;
}

} // namespace eternity2_v2
