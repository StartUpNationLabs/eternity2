//
// Common piece utility functions shared between solver versions
// Inline implementations for maximum performance in hot paths
//

#ifndef ETERNITY2_COMMON_PIECE_UTILS_H
#define ETERNITY2_COMMON_PIECE_UTILS_H

#include "types.h"
#include <vector>

namespace eternity2_common {

/**
 * @brief Create a piece from four parts (top, right, bottom, left)
 * Inline for performance - called frequently during domain initialization
 */
[[gnu::always_inline]] inline Piece make_piece(PiecePart top, PiecePart right, PiecePart down, PiecePart left)
{
    return static_cast<Piece>(left) | (static_cast<Piece>(down) << 16U) | (static_cast<Piece>(right) << 32U)
           | (static_cast<Piece>(top) << 48U);
}

/**
 * @brief Rotate a piece right (clockwise) n times
 * HOT PATH - Inline for performance, called millions of times during search
 */
[[gnu::always_inline]] inline Piece rotate_piece_right(Piece piece, int n)
{
    if (n == 0) return piece;
    const unsigned shift = 16U * static_cast<unsigned>(n);
    return (piece >> shift) | (piece << (64U - shift));
}

/**
 * @brief Rotate a piece left (counter-clockwise) n times
 * Inline for performance
 */
[[gnu::always_inline]] inline Piece rotate_piece_left(Piece piece, int n)
{
    if (n == 0) return piece;
    const unsigned shift = 16U * static_cast<unsigned>(n);
    return (piece << shift) | (piece >> (64U - shift));
}

/**
 * @brief Extract a specific part from a piece using a mask
 * HOT PATH - Inline for performance, called millions of times during constraint filtering
 */
[[gnu::always_inline]] inline PiecePart get_piece_part(Piece piece, Piece mask)
{
    // Compute shift amount based on mask (branchless using lookup)
    constexpr unsigned shifts[4] = {0U, 16U, 32U, 48U};  // LEFT, DOWN, RIGHT, UP
    const unsigned shift = (mask == UP_MASK) ? 48U :
                          (mask == RIGHT_MASK) ? 32U :
                          (mask == DOWN_MASK) ? 16U : 0U;
    return static_cast<PiecePart>((piece & mask) >> shift);
}

/**
 * @brief Extract edge value by direction (0=UP, 1=RIGHT, 2=DOWN, 3=LEFT)
 * Optimized version using direction index instead of mask comparison
 */
[[gnu::always_inline]] inline PiecePart get_edge_by_direction(Piece piece, int direction)
{
    constexpr unsigned shifts[4] = {48U, 32U, 16U, 0U};  // UP, RIGHT, DOWN, LEFT
    constexpr Piece masks[4] = {UP_MASK, RIGHT_MASK, DOWN_MASK, LEFT_MASK};
    return static_cast<PiecePart>((piece & masks[direction]) >> shifts[direction]);
}

} // namespace eternity2_common

#endif // ETERNITY2_COMMON_PIECE_UTILS_H

