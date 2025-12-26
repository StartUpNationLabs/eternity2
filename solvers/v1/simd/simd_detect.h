//
// SIMD Detection and Configuration
//

#ifndef ETERNITY2_SIMD_DETECT_H
#define ETERNITY2_SIMD_DETECT_H

// Compile-time SIMD detection based on compiler flags and architecture
#if defined(__ARM_NEON) || defined(__ARM_NEON__)
    #define ETERNITY2_SIMD_NEON 1
    #define ETERNITY2_SIMD_WIDTH 2
    #define ETERNITY2_SIMD_ALIGNMENT 16
    #define ETERNITY2_SIMD_NAME "ARM NEON"
#elif defined(__AVX512F__) && defined(__AVX512BW__)
    #define ETERNITY2_SIMD_AVX512 1
    #define ETERNITY2_SIMD_WIDTH 8
    #define ETERNITY2_SIMD_ALIGNMENT 64
    #define ETERNITY2_SIMD_NAME "AVX-512"
#elif defined(__AVX2__)
    #define ETERNITY2_SIMD_AVX2 1
    #define ETERNITY2_SIMD_WIDTH 4
    #define ETERNITY2_SIMD_ALIGNMENT 32
    #define ETERNITY2_SIMD_NAME "AVX2"
#else
    #define ETERNITY2_SIMD_SCALAR 1
    #define ETERNITY2_SIMD_WIDTH 1
    #define ETERNITY2_SIMD_ALIGNMENT 8
    #define ETERNITY2_SIMD_NAME "Scalar"
#endif

#include <cstddef>

namespace eternity2 {
namespace simd {

// Enum for SIMD capability
enum class Capability {
    Scalar,
    NEON,
    AVX2,
    AVX512
};

// Get the compile-time determined SIMD capability
constexpr Capability get_capability() {
#if defined(ETERNITY2_SIMD_AVX512)
    return Capability::AVX512;
#elif defined(ETERNITY2_SIMD_AVX2)
    return Capability::AVX2;
#elif defined(ETERNITY2_SIMD_NEON)
    return Capability::NEON;
#else
    return Capability::Scalar;
#endif
}

// Get the SIMD width (number of 64-bit values processed in parallel)
constexpr size_t get_width() {
    return ETERNITY2_SIMD_WIDTH;
}

// Get the required memory alignment for SIMD operations
constexpr size_t get_alignment() {
    return ETERNITY2_SIMD_ALIGNMENT;
}

// Get the name of the SIMD instruction set
constexpr const char* get_name() {
    return ETERNITY2_SIMD_NAME;
}

} // namespace simd
} // namespace eternity2

#endif // ETERNITY2_SIMD_DETECT_H
