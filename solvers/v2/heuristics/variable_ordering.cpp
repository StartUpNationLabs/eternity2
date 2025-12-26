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

VariableSelection select_variable_border_first(const DomainManager& domain_manager) {
    VariableSelection result;
    result.domain_size = std::numeric_limits<size_t>::max();
    result.degree = 0;
    result.is_failure = false;
    result.index = {0, 0};

    // Phase tracking: 0 = border (corners + edges), 1 = interior
    // Check if border is complete by scanning for unassigned border positions
    bool border_complete = true;
    for (size_t y = 0; y < domain_manager.board_size(); ++y) {
        for (size_t x = 0; x < domain_manager.board_size(); ++x) {
            Index index = {x, y};
            const DomainEntry& domain = domain_manager.get_domain(index);
            
            // Check if this is a border position (corner or edge)
            bool is_border = (x == 0 || x == domain_manager.board_size() - 1 ||
                             y == 0 || y == domain_manager.board_size() - 1);
            
            if (is_border && !domain.is_assigned) {
                border_complete = false;
                break;
            }
        }
        if (!border_complete) break;
    }

    // Phase 1: Border positions only (corners first, then edges)
    // Phase 2: Interior positions (only if border is complete)
    bool found_unassigned = false;
    
    // Priority order: corners (priority 0), edges (priority 1), interior (priority 2)
    // Start with highest priority we want to consider
    int min_priority_to_consider = border_complete ? 2 : 0;  // Start with corners if border incomplete
    
    // Try each priority level in order until we find unassigned positions
    for (int target_priority = 0; target_priority <= 2; ++target_priority) {
        // Skip priorities below our minimum
        if (target_priority < min_priority_to_consider) {
            continue;
        }
        
        // Reset for this priority level
        bool found_in_this_priority = false;
        size_t best_domain_size = std::numeric_limits<size_t>::max();
        size_t best_degree = 0;
        Index best_index = {0, 0};
        
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

                // Determine position priority
                int priority;
                if (domain_manager.is_corner(index)) {
                    priority = 0;  // Corners first
                } else if (domain_manager.is_edge(index)) {
                    priority = 1;  // Edges second
                } else {
                    priority = 2;  // Interior last
                }

                // Only consider positions matching current target priority
                if (priority != target_priority) {
                    continue;
                }

                found_in_this_priority = true;
                size_t domain_size = domain.size();
                size_t degree = domain_manager.count_unassigned_neighbors(index);

                // MRV: prefer smaller domains
                // Degree: prefer higher degree as tie-breaker
                if (domain_size < best_domain_size ||
                    (domain_size == best_domain_size && degree > best_degree)) {
                    best_index = index;
                    best_domain_size = domain_size;
                    best_degree = degree;
                }
            }
        }
        
        // If we found positions in this priority level, use the best one
        if (found_in_this_priority) {
            result.index = best_index;
            result.domain_size = best_domain_size;
            result.degree = best_degree;
            break;  // Found a variable, stop searching
        }
    }

    // If no unassigned found, solution is complete
    if (!found_unassigned) {
        result.domain_size = 0;
        result.is_failure = false;  // Not a failure, just complete
    }

    return result;
}

} // namespace eternity2_v2
