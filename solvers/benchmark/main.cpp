#include "benchmark.h"
#include "common/utils.h"
#include <iostream>
#include <filesystem>
#include <algorithm>
#include <cstring>
#include <stdexcept>

namespace fs = std::filesystem;

void print_usage(const char* program_name) {
    std::cout << "Eternity II Solver Benchmark Tool" << std::endl;
    std::cout << "Compares V1 (baseline) and V2 (MAC+MRV+LCV) solvers\n" << std::endl;

    std::cout << "Usage: " << program_name << " [options] <puzzle_file_or_directory>" << std::endl;
    std::cout << "\nOptions:" << std::endl;
    std::cout << "  --timeout <ms>     Timeout per puzzle (default: 60000ms)" << std::endl;
    std::cout << "  --csv <file>       Export results to CSV file" << std::endl;
    std::cout << "  --verbose          Show detailed progress" << std::endl;
    std::cout << "  --quiet            Minimal output (results only)" << std::endl;
    std::cout << "  --no-mrv           Disable MRV heuristic in V2" << std::endl;
    std::cout << "  --no-degree        Disable degree heuristic in V2" << std::endl;
    std::cout << "  --no-lcv           Disable LCV heuristic in V2" << std::endl;
    std::cout << "  --v1-only          Run V1 only" << std::endl;
    std::cout << "  --v2-only          Run V2 only (for ablation studies)" << std::endl;
    std::cout << "  --sequential       Run puzzles sequentially (default: parallel)" << std::endl;
    std::cout << "  --table            Show results as table (default)" << std::endl;
    std::cout << "  --detailed         Show detailed comparison for each puzzle" << std::endl;
    std::cout << "  --export-solutions Export solved boards to CSV files" << std::endl;
    std::cout << "                     (creates 'solutions' directory next to puzzle files)" << std::endl;
    std::cout << "  --help             Show this help message" << std::endl;

    std::cout << "\nExamples:" << std::endl;
    std::cout << "  " << program_name << " puzzle.csv" << std::endl;
    std::cout << "  " << program_name << " --timeout 30000 data/puzzles/" << std::endl;
    std::cout << "  " << program_name << " --csv results.csv --verbose data/puzzles/" << std::endl;
}

std::vector<std::string> find_puzzle_files(const std::string& path) {
    std::vector<std::string> files;

    if (fs::is_regular_file(path)) {
        // Single file
        if (path.ends_with(".csv")) {
            files.push_back(path);
        }
    } else if (fs::is_directory(path)) {
        // Directory - find all CSV files
        for (const auto& entry : fs::directory_iterator(path)) {
            if (entry.is_regular_file() && entry.path().extension() == ".csv") {
                files.push_back(entry.path().string());
            }
        }
        // Sort by filename for consistent ordering
        std::sort(files.begin(), files.end());
    }

    return files;
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    // Parse arguments
    eternity2_benchmark::BenchmarkConfig config;
    std::string input_path;
    std::string csv_output;
    bool show_detailed = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];

        if (arg == "--help" || arg == "-h") {
            print_usage(argv[0]);
            return 0;
        } else if (arg == "--timeout" && i + 1 < argc) {
            try {
                config.timeout_ms = eternity2_utils::safe_stoul(argv[++i]);
            } catch (const eternity2_utils::ConversionError& e) {
                std::cerr << "Error: Invalid timeout value: " << e.what() << std::endl;
                return 1;
            }
        } else if (arg == "--csv" && i + 1 < argc) {
            csv_output = argv[++i];
        } else if (arg == "--verbose") {
            config.verbose = true;
            config.show_progress = true;
        } else if (arg == "--quiet") {
            config.verbose = false;
            config.show_progress = false;
        } else if (arg == "--no-mrv") {
            config.v2_use_mrv = false;
        } else if (arg == "--no-degree") {
            config.v2_use_degree = false;
        } else if (arg == "--no-lcv") {
            config.v2_use_lcv = false;
        } else if (arg == "--v1-only") {
            config.run_v1 = true;
            config.run_v2 = false;
        } else if (arg == "--v2-only") {
            config.run_v1 = false;
            config.run_v2 = true;
        } else if (arg == "--sequential") {
            config.parallel = false;
        } else if (arg == "--table") {
            show_detailed = false;
        } else if (arg == "--detailed") {
            show_detailed = true;
        } else if (arg == "--export-solutions") {
            config.export_solutions = true;
        } else if (arg[0] != '-') {
            input_path = arg;
        } else {
            std::cerr << "Unknown option: " << arg << std::endl;
            print_usage(argv[0]);
            return 1;
        }
    }

    if (input_path.empty()) {
        std::cerr << "Error: No puzzle file or directory specified" << std::endl;
        print_usage(argv[0]);
        return 1;
    }

    // Find puzzle files
    auto puzzle_files = find_puzzle_files(input_path);

    if (puzzle_files.empty()) {
        std::cerr << "Error: No puzzle files found in " << input_path << std::endl;
        return 1;
    }

    std::cout << "Eternity II Solver Benchmark" << std::endl;
    std::cout << "============================" << std::endl;
    std::cout << "Found " << puzzle_files.size() << " puzzle(s) to benchmark" << std::endl;
    std::cout << "Timeout: " << config.timeout_ms << "ms per puzzle" << std::endl;
    std::cout << "Mode: " << (config.parallel ? "parallel" : "sequential") << std::endl;

    // Show which solvers are being run
    std::cout << "Solvers: ";
    if (config.run_v1 && config.run_v2) {
        std::cout << "V1 vs V2 comparison";
    } else if (config.run_v1) {
        std::cout << "V1 only";
    } else if (config.run_v2) {
        std::cout << "V2 only";
    }
    std::cout << std::endl;

    // Show V2 configuration if V2 is enabled
    if (config.run_v2) {
        std::cout << "V2 Heuristics: ";
        std::cout << (config.v2_use_mrv ? "MRV " : "");
        std::cout << (config.v2_use_degree ? "Degree " : "");
        std::cout << (config.v2_use_lcv ? "LCV " : "");
        if (!config.v2_use_mrv && !config.v2_use_degree && !config.v2_use_lcv) {
            std::cout << "(none - random ordering)";
        }
        std::cout << std::endl;
    }
    std::cout << std::endl;

    // Run benchmarks
    eternity2_benchmark::Benchmark benchmark(config);
    auto results = benchmark.run_all(puzzle_files);

    // Display results
    if (show_detailed) {
        for (const auto& comp : results) {
            eternity2_benchmark::Benchmark::print_comparison(comp);
        }
    } else {
        eternity2_benchmark::Benchmark::print_table(results);
    }

    // Print summary
    auto summary = eternity2_benchmark::Benchmark::summarize(results);
    eternity2_benchmark::Benchmark::print_summary(summary);

    // Export CSV if requested
    if (!csv_output.empty()) {
        eternity2_benchmark::Benchmark::export_csv(results, csv_output);
    }

    return 0;
}
