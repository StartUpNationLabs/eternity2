//
// SIMD-accelerated domain filtering for Eternity II Solver v2
// Supports ARM NEON (Apple Silicon) and x86 AVX2
//
// NOTE: The batch filtering functions in this header are NOT currently used
// because the AoS (Array of Structures) memory layout requires expensive
// gather operations that negate SIMD benefits. These functions are preserved
// for future use when domains are converted to bitset representation (Step 2),
// which will make SIMD operations truly beneficial.
//
// Current optimization: Explicit loops with pointer arithmetic in domain.cpp
// are faster than std::remove_if with lambda but slower than true SIMD.
//

#ifndef ETERNITY2_V2_SIMD_FILTER_H
#define ETERNITY2_V2_SIMD_FILTER_H

#include "common/types.h"
#include <cstdint>
#include <cstddef>
#include <bitset>

// Detect SIMD support
#if defined(__ARM_NEON) || defined(__ARM_NEON__)
    #define ETERNITY2_USE_NEON 1
    #include <arm_neon.h>
#elif defined(__AVX2__)
    #define ETERNITY2_USE_AVX2 1
    #include <immintrin.h>
#else
    #define ETERNITY2_USE_SCALAR 1
#endif

namespace eternity2_v2 {
namespace simd {

using eternity2_common::RotatedPiece;
using eternity2_common::PiecePart;

// Direction indices matching domain.cpp
constexpr int SIMD_DIR_UP = 0;
constexpr int SIMD_DIR_RIGHT = 1;
constexpr int SIMD_DIR_DOWN = 2;
constexpr int SIMD_DIR_LEFT = 3;

/**
 * @brief Get edge value from RotatedPiece for given direction
 * Always inline for performance
 */
[[gnu::always_inline]]
inline PiecePart get_edge_for_direction(const RotatedPiece& rp, int direction) {
    switch (direction) {
        case SIMD_DIR_UP:    return rp.edge_up;
        case SIMD_DIR_RIGHT: return rp.edge_right;
        case SIMD_DIR_DOWN:  return rp.edge_down;
        case SIMD_DIR_LEFT:  return rp.edge_left;
        default:             return 0;
    }
}

#ifdef ETERNITY2_USE_NEON

/**
 * @brief Check if 8 pieces match the constraint using NEON
 *
 * @param pieces Pointer to array of 8 RotatedPiece
 * @param direction Edge direction to check
 * @param constraint Edge value that must match
 * @return Bitmask where bit i is set if pieces[i] matches
 */
[[gnu::always_inline]]
inline uint8_t check_8_pieces_neon(
    const RotatedPiece* pieces,
    int direction,
    PiecePart constraint)
{
    // Gather edges from 8 pieces (manual gather since NEON lacks it)
    alignas(16) uint16_t edges[8];
    for (int i = 0; i < 8; ++i) {
        edges[i] = get_edge_for_direction(pieces[i], direction);
    }

    // Load edges into NEON registers (2 x uint16x4)
    uint16x4_t edges_lo = vld1_u16(edges);
    uint16x4_t edges_hi = vld1_u16(edges + 4);

    // Broadcast constraint to vector
    uint16x4_t constraint_vec = vdup_n_u16(constraint);

    // Compare: result is 0xFFFF for match, 0x0000 for no match
    uint16x4_t match_lo = vceq_u16(edges_lo, constraint_vec);
    uint16x4_t match_hi = vceq_u16(edges_hi, constraint_vec);

    // Narrow to 8-bit (0xFF or 0x00 per lane)
    uint8x8_t narrow_lo = vmovn_u16(vcombine_u16(match_lo, match_hi));

    // Extract mask by checking high bit of each byte
    // Shift each byte right by 7 to get 0 or 1, then pack into bits
    uint8_t mask = 0;
    alignas(8) uint8_t narrow_arr[8];
    vst1_u8(narrow_arr, narrow_lo);

    for (int i = 0; i < 8; ++i) {
        if (narrow_arr[i]) mask |= (1u << i);
    }

    return mask;
}

/**
 * @brief Check piece availability for 8 pieces using NEON
 *
 * @param pieces Pointer to array of 8 RotatedPiece
 * @param availability Bitset of available pieces
 * @return Bitmask where bit i is set if pieces[i].index is available
 */
template<size_t N>
[[gnu::always_inline]]
inline uint8_t check_8_availability_neon(
    const RotatedPiece* pieces,
    const std::bitset<N>& availability)
{
    uint8_t mask = 0;
    for (int i = 0; i < 8; ++i) {
        if (availability.test(pieces[i].index)) {
            mask |= (1u << i);
        }
    }
    return mask;
}

/**
 * @brief Combined check: match constraint AND available
 */
template<size_t N>
[[gnu::always_inline]]
inline uint8_t filter_8_pieces_neon(
    const RotatedPiece* pieces,
    int direction,
    PiecePart constraint,
    const std::bitset<N>& availability)
{
    uint8_t edge_match = check_8_pieces_neon(pieces, direction, constraint);
    uint8_t avail_mask = check_8_availability_neon(pieces, availability);
    return edge_match & avail_mask;
}

#endif // ETERNITY2_USE_NEON

#ifdef ETERNITY2_USE_AVX2

/**
 * @brief Check if 16 pieces match the constraint using AVX2
 */
[[gnu::always_inline]]
inline uint16_t check_16_pieces_avx2(
    const RotatedPiece* pieces,
    int direction,
    PiecePart constraint)
{
    // Gather edges from 16 pieces
    alignas(32) uint16_t edges[16];
    for (int i = 0; i < 16; ++i) {
        edges[i] = get_edge_for_direction(pieces[i], direction);
    }

    // Load edges into AVX2 register
    __m256i edges_vec = _mm256_load_si256((__m256i*)edges);

    // Broadcast constraint
    __m256i constraint_vec = _mm256_set1_epi16(constraint);

    // Compare: result is 0xFFFF for match, 0x0000 for no match
    __m256i match = _mm256_cmpeq_epi16(edges_vec, constraint_vec);

    // Pack to bytes and extract mask
    // Each 16-bit lane becomes a bit in the result
    return static_cast<uint16_t>(_mm256_movemask_epi8(match)) & 0x5555;
    // Note: movemask gives us pairs of bits, we'd need to extract properly
    // This is a simplified version - full implementation would need careful handling
}

#endif // ETERNITY2_USE_AVX2

/**
 * @brief Scalar fallback: check if 8 pieces match constraint
 */
[[gnu::always_inline]]
inline uint8_t check_8_pieces_scalar(
    const RotatedPiece* pieces,
    int direction,
    PiecePart constraint)
{
    uint8_t mask = 0;
    for (int i = 0; i < 8; ++i) {
        if (get_edge_for_direction(pieces[i], direction) == constraint) {
            mask |= (1u << i);
        }
    }
    return mask;
}

/**
 * @brief Scalar fallback: combined filter
 */
template<size_t N>
[[gnu::always_inline]]
inline uint8_t filter_8_pieces_scalar(
    const RotatedPiece* pieces,
    int direction,
    PiecePart constraint,
    const std::bitset<N>& availability)
{
    uint8_t mask = 0;
    for (int i = 0; i < 8; ++i) {
        bool edge_ok = (get_edge_for_direction(pieces[i], direction) == constraint);
        bool avail_ok = availability.test(pieces[i].index);
        if (edge_ok && avail_ok) {
            mask |= (1u << i);
        }
    }
    return mask;
}

/**
 * @brief Platform-independent filter for 8 pieces
 * Returns bitmask of pieces that pass both edge match and availability checks
 */
template<size_t N>
[[gnu::always_inline]]
inline uint8_t filter_8_pieces(
    const RotatedPiece* pieces,
    int direction,
    PiecePart constraint,
    const std::bitset<N>& availability)
{
#ifdef ETERNITY2_USE_NEON
    return filter_8_pieces_neon(pieces, direction, constraint, availability);
#elif defined(ETERNITY2_USE_AVX2)
    // For AVX2, fall back to scalar for now (8 pieces)
    // AVX2 is better suited for 16+ pieces at once
    return filter_8_pieces_scalar(pieces, direction, constraint, availability);
#else
    return filter_8_pieces_scalar(pieces, direction, constraint, availability);
#endif
}

/**
 * @brief Count set bits in a byte (population count)
 */
[[gnu::always_inline]]
inline int popcount8(uint8_t x) {
#if defined(__GNUC__) || defined(__clang__)
    return __builtin_popcount(x);
#else
    x = x - ((x >> 1) & 0x55);
    x = (x & 0x33) + ((x >> 2) & 0x33);
    return (x + (x >> 4)) & 0x0F;
#endif
}

} // namespace simd
} // namespace eternity2_v2

#endif // ETERNITY2_V2_SIMD_FILTER_H
