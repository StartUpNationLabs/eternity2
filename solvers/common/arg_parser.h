//
// Common argument parsing utilities for solver executables
//

#ifndef ETERNITY2_ARG_PARSER_H
#define ETERNITY2_ARG_PARSER_H

#include <string>
#include <vector>
#include "v2/solver/solver_v2.h"

namespace eternity2_arg_parser {

/**
 * @brief Parse solver v2 configuration from command line arguments
 * 
 * @param argc Number of arguments
 * @param argv Argument vector
 * @param config Output solver configuration
 * @param filename Output puzzle filename
 * @param print_stats Output flag for printing statistics
 * @param quiet Output flag for quiet mode
 * @param partition_depth Output partition depth for parallel mode
 * @return true if parsing succeeded, false if help was requested
 * @throws std::runtime_error if argument parsing fails
 */
bool parse_v2_arguments(int argc, char* argv[],
                       eternity2_v2::SolverConfig& config,
                       std::string& filename,
                       bool& print_stats,
                       bool& quiet,
                       size_t& partition_depth);

/**
 * @brief Print usage information for solver v2
 * 
 * @param program_name Name of the program executable
 */
void print_v2_usage(const char* program_name);

} // namespace eternity2_arg_parser

#endif // ETERNITY2_ARG_PARSER_H

