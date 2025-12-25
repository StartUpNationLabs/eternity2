//
// SIMD Operations Implementation
//

#include "simd_ops.h"

// Include SIMD intrinsics based on detected architecture
#if defined(ETERNITY2_SIMD_AVX512)
#include <immintrin.h>
#elif defined(ETERNITY2_SIMD_AVX2)
#include <immintrin.h>
#elif defined(ETERNITY2_SIMD_NEON)
#include <arm_neon.h>
#endif

namespace eternity2 {
namespace simd {

#if defined(ETERNITY2_SIMD_AVX512)
// AVX-512 implementation: 8 pieces per batch
template<>
BatchResult<8> batch_match<8>(Piece query_piece, Piece query_mask, const Piece* pieces) {
    BatchResult<8> result;

    // Broadcast query piece and mask to 512-bit vectors
    __m512i piece_vec = _mm512_set1_epi64(static_cast<int64_t>(query_piece));
    __m512i mask_vec = _mm512_set1_epi64(static_cast<int64_t>(query_mask));

    // Load 8 pieces from aligned memory
    __m512i data_vec = _mm512_load_si512(reinterpret_cast<const __m512i*>(pieces));

    // XOR with query piece
    __m512i xor_result = _mm512_xor_si512(piece_vec, data_vec);

    // AND with mask
    __m512i masked = _mm512_and_si512(xor_result, mask_vec);

    // Compare with zero (match if all masked bits are zero)
    __mmask8 cmp_mask = _mm512_cmpeq_epi64_mask(masked, _mm512_setzero_si512());

    // Extract results
    for (int i = 0; i < 8; ++i) {
        result.matches[i] = (cmp_mask >> i) & 1;
        if (result.matches[i]) result.match_count++;
    }

    return result;
}
#endif

#if defined(ETERNITY2_SIMD_AVX2)
// AVX2 implementation: 4 pieces per batch
template<>
BatchResult<4> batch_match<4>(Piece query_piece, Piece query_mask, const Piece* pieces) {
    BatchResult<4> result;

    // Broadcast query piece and mask to 256-bit vectors
    __m256i piece_vec = _mm256_set1_epi64x(static_cast<int64_t>(query_piece));
    __m256i mask_vec = _mm256_set1_epi64x(static_cast<int64_t>(query_mask));

    // Load 4 pieces from aligned memory
    __m256i data_vec = _mm256_load_si256(reinterpret_cast<const __m256i*>(pieces));

    // XOR with query piece
    __m256i xor_result = _mm256_xor_si256(piece_vec, data_vec);

    // AND with mask
    __m256i masked = _mm256_and_si256(xor_result, mask_vec);

    // Compare with zero
    __m256i cmp = _mm256_cmpeq_epi64(masked, _mm256_setzero_si256());

    // Extract comparison mask
    int mask_bits = _mm256_movemask_epi8(cmp);

    // Each 64-bit lane produces 8 bytes of mask (all 0xFF if match, 0x00 if no match)
    for (int i = 0; i < 4; ++i) {
        result.matches[i] = (mask_bits & (0xFF << (i * 8))) == (0xFF << (i * 8));
        if (result.matches[i]) result.match_count++;
    }

    return result;
}
#endif

#if defined(ETERNITY2_SIMD_NEON)
// ARM NEON implementation: 2 pieces per batch
template<>
BatchResult<2> batch_match<2>(Piece query_piece, Piece query_mask, const Piece* pieces) {
    BatchResult<2> result;

    // Broadcast query piece and mask to 128-bit vectors
    uint64x2_t piece_vec = vdupq_n_u64(query_piece);
    uint64x2_t mask_vec = vdupq_n_u64(query_mask);

    // Load 2 pieces from aligned memory
    uint64x2_t data_vec = vld1q_u64(pieces);

    // XOR with query piece
    uint64x2_t xor_result = veorq_u64(piece_vec, data_vec);

    // AND with mask
    uint64x2_t masked = vandq_u64(xor_result, mask_vec);

    // Compare with zero (result is all 1s if equal, all 0s if not equal)
    uint64x2_t cmp = vceqq_u64(masked, vdupq_n_u64(0));

    // Extract results (check if all bits are set)
    result.matches[0] = vgetq_lane_u64(cmp, 0) == ~0ULL;
    result.matches[1] = vgetq_lane_u64(cmp, 1) == ~0ULL;
    result.match_count = result.matches[0] + result.matches[1];

    return result;
}
#endif

// Scalar fallback - always available
template<>
BatchResult<1> batch_match<1>(Piece query_piece, Piece query_mask, const Piece* pieces) {
    BatchResult<1> result;

    // Simple XOR and AND
    Piece xor_result = query_piece ^ pieces[0];
    result.matches[0] = (xor_result & query_mask) == 0;
    result.match_count = result.matches[0] ? 1 : 0;

    return result;
}

} // namespace simd
} // namespace eternity2
