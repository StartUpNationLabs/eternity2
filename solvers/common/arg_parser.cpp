//
// Common argument parsing utilities implementation
//

#include "arg_parser.h"
#include "utils.h"
#include <iostream>

namespace eternity2_arg_parser {

void print_v2_usage(const char* program_name) {
    std::cout << "Eternity II Solver v2 - Optimized with MAC, MRV, LCV\n\n";
    std::cout << "Usage: " << program_name << " [options] <puzzle_file.csv>\n\n";
    std::cout << "Options:\n";
    std::cout << "  --no-mrv        Disable MRV variable ordering\n";
    std::cout << "  --no-degree     Disable degree heuristic (MRV tie-breaker)\n";
    std::cout << "  --no-lcv        Disable LCV value ordering\n";
    std::cout << "  --random        Use random value ordering (disables LCV)\n";
    std::cout << "  --verbose       Print detailed progress\n";
    std::cout << "  --quiet         Minimal output\n";
    std::cout << "  --stats         Print statistics at end\n";
    std::cout << "  --timeout <ms>  Set timeout in milliseconds\n";
    std::cout << "  --parallel      Enable parallel search mode\n";
    std::cout << "  --threads <n>   Set number of worker threads (default: auto-detect)\n";
    std::cout << "  --partition-depth <n>  Set partition depth for parallel mode (default: auto)\n";
    std::cout << "  --help          Show this help message\n";
    std::cout << "\nExamples:\n";
    std::cout << "  " << program_name << " puzzle.csv              # Solve with all optimizations\n";
    std::cout << "  " << program_name << " --no-lcv puzzle.csv     # Disable LCV only\n";
    std::cout << "  " << program_name << " --verbose puzzle.csv    # Verbose output\n";
    std::cout << "  " << program_name << " --parallel puzzle.csv   # Use all CPU cores\n";
    std::cout << "  " << program_name << " --threads 4 puzzle.csv  # Use 4 threads\n";
}

bool parse_v2_arguments(int argc, char* argv[],
                       eternity2_v2::SolverConfig& config,
                       std::string& filename,
                       bool& print_stats,
                       bool& quiet,
                       size_t& partition_depth) {
    // Initialize defaults
    config.verbose = false;
    print_stats = true;
    quiet = false;
    partition_depth = 0;  // 0 = auto-detect
    filename.clear();

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];

        if (arg == "--help" || arg == "-h") {
            print_v2_usage(argv[0]);
            return false;  // Help requested, don't continue
        } else if (arg == "--no-mrv") {
            config.use_mrv = false;
        } else if (arg == "--no-degree") {
            config.use_degree = false;
        } else if (arg == "--no-lcv") {
            config.use_lcv = false;
        } else if (arg == "--random") {
            config.use_lcv = false;
        } else if (arg == "--verbose" || arg == "-v") {
            config.verbose = true;
        } else if (arg == "--quiet" || arg == "-q") {
            quiet = true;
            config.verbose = false;
        } else if (arg == "--stats") {
            print_stats = true;
        } else if (arg == "--timeout" && i + 1 < argc) {
            try {
                config.max_time_ms = eternity2_utils::safe_stoul(argv[++i]);
            } catch (const eternity2_utils::ConversionError& e) {
                throw std::runtime_error("Invalid timeout value: " + std::string(e.what()));
            }
        } else if (arg == "--parallel") {
            config.parallel_enabled = true;
            if (config.num_threads <= 1) {
                config.num_threads = 0;  // 0 = auto-detect in ParallelSolverV2
            }
        } else if (arg == "--threads" && i + 1 < argc) {
            try {
                config.num_threads = eternity2_utils::safe_stoul(argv[++i]);
                if (config.num_threads > 1) {
                    config.parallel_enabled = true;
                }
            } catch (const eternity2_utils::ConversionError& e) {
                throw std::runtime_error("Invalid thread count: " + std::string(e.what()));
            }
        } else if (arg == "--partition-depth" && i + 1 < argc) {
            try {
                partition_depth = eternity2_utils::safe_stoul(argv[++i]);
            } catch (const eternity2_utils::ConversionError& e) {
                throw std::runtime_error("Invalid partition depth: " + std::string(e.what()));
            }
        } else if (arg[0] != '-') {
            filename = arg;
        } else {
            throw std::runtime_error("Unknown option: " + arg);
        }
    }

    if (filename.empty()) {
        throw std::runtime_error("No puzzle file specified");
    }

    return true;  // Success
}

} // namespace eternity2_arg_parser

