//
// SIMD Operations for Piece Matching
//

#ifndef ETERNITY2_SIMD_OPS_H
#define ETERNITY2_SIMD_OPS_H

#include "simd_detect.h"
#include "common/types.h"
#include "common/piece_utils.h"
#include <array>
#include <cstdint>
#include <cstdlib>
#include <new>

namespace eternity2 {
namespace simd {

using eternity2_common::Piece;

// Aligned memory allocator for SIMD operations
template<typename T, size_t Alignment = ETERNITY2_SIMD_ALIGNMENT>
class AlignedAllocator {
public:
    using value_type = T;

    T* allocate(size_t n) {
        void* ptr = nullptr;
#ifdef _MSC_VER
        ptr = _aligned_malloc(n * sizeof(T), Alignment);
        if (!ptr) throw std::bad_alloc();
#else
        if (posix_memalign(&ptr, Alignment, n * sizeof(T)) != 0) {
            throw std::bad_alloc();
        }
#endif
        return static_cast<T*>(ptr);
    }

    void deallocate(T* p, size_t) {
#ifdef _MSC_VER
        _aligned_free(p);
#else
        free(p);
#endif
    }

    template<typename U>
    struct rebind {
        using other = AlignedAllocator<U, Alignment>;
    };
};

// SIMD batch comparison result
template<size_t Width>
struct BatchResult {
    std::array<bool, Width> matches;
    size_t match_count;

    BatchResult() : matches{}, match_count(0) {}
};

// Core SIMD operation: batch XOR-AND-compare
// Returns which pieces match the query: (piece XOR query_piece) & query_mask == 0
// pieces must be aligned to ETERNITY2_SIMD_ALIGNMENT
template<size_t Width>
BatchResult<Width> batch_match(
    Piece query_piece,
    Piece query_mask,
    const Piece* pieces  // Must be aligned
);

// Specializations for different SIMD widths
// Implementations are in simd_ops.cpp

#if defined(ETERNITY2_SIMD_AVX512)
template<>
BatchResult<8> batch_match<8>(Piece query_piece, Piece query_mask, const Piece* pieces);
#endif

#if defined(ETERNITY2_SIMD_AVX2)
template<>
BatchResult<4> batch_match<4>(Piece query_piece, Piece query_mask, const Piece* pieces);
#endif

#if defined(ETERNITY2_SIMD_NEON)
template<>
BatchResult<2> batch_match<2>(Piece query_piece, Piece query_mask, const Piece* pieces);
#endif

// Scalar fallback - always available
template<>
BatchResult<1> batch_match<1>(Piece query_piece, Piece query_mask, const Piece* pieces);

} // namespace simd
} // namespace eternity2

#endif // ETERNITY2_SIMD_OPS_H
