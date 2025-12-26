//
// Common constants for Eternity II solvers
//

#ifndef ETERNITY2_CONSTANTS_H
#define ETERNITY2_CONSTANTS_H

#include <cstddef>
#include <chrono>

namespace eternity2_constants {

// Threading constants
constexpr unsigned long DEFAULT_THREAD_COUNT = 16;
constexpr unsigned long MIN_THREAD_COUNT = 1;
constexpr unsigned long MAX_THREAD_COUNT = 256;  // Reasonable upper limit

// Timing constants
constexpr std::chrono::nanoseconds PROGRESS_CHECK_INTERVAL_NS{200};
constexpr std::chrono::milliseconds DEFAULT_TIMEOUT_MS{60000};
constexpr std::chrono::milliseconds DEFAULT_WAIT_TIME_MS{2000};

// Hash table constants
constexpr unsigned int DEFAULT_HASH_LENGTH_THRESHOLD = 7;
constexpr unsigned int MIN_HASH_LENGTH_THRESHOLD = 1;
constexpr unsigned int MAX_HASH_LENGTH_THRESHOLD = 16;

// Job management constants
constexpr int DEFAULT_MAX_CONCURRENT_JOBS = 10;
constexpr int MIN_MAX_CONCURRENT_JOBS = 1;
constexpr int MAX_MAX_CONCURRENT_JOBS = 100;

// Board size constants
constexpr int MIN_BOARD_SIZE = 1;
constexpr int MAX_BOARD_SIZE = 256;  // Reasonable upper limit

// Parallel solver constants
constexpr size_t DEFAULT_PARTITION_DEPTH = 0;  // 0 = auto-detect
constexpr size_t MIN_PARTITION_DEPTH = 1;
constexpr size_t MAX_PARTITION_DEPTH = 10;

// Progress reporting constants
constexpr int MAX_RESPONSES_TO_SEND = 10;  // For step-by-step solver

} // namespace eternity2_constants

#endif // ETERNITY2_CONSTANTS_H

