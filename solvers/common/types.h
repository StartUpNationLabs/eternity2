//
// Common type definitions shared between solver versions
//

#ifndef ETERNITY2_COMMON_TYPES_H
#define ETERNITY2_COMMON_TYPES_H

#include <vector>
#include <utility>

namespace eternity2_common {

// Forward declarations
using Piece = unsigned long long;
using PiecePart = unsigned short;

// Piece constants
constexpr Piece TRUE       = 0b1111111111111111;
constexpr Piece UP_MASK    = 0b1111111111111111000000000000000000000000000000000000000000000000;
constexpr Piece RIGHT_MASK = 0b0000000000000000111111111111111100000000000000000000000000000000;
constexpr Piece DOWN_MASK  = 0b0000000000000000000000000000000011111111111111110000000000000000;
constexpr Piece LEFT_MASK  = 0b0000000000000000000000000000000000000000000000001111111111111111;
constexpr PiecePart WALL   = 0b1111111111111111;
constexpr Piece EMPTY      = 0b0000000000000000;
constexpr Piece FULLWALL   = UP_MASK | RIGHT_MASK | DOWN_MASK | LEFT_MASK;

/**
 * @brief Represents a piece with rotation and index information
 * 
 * This structure is used by both v1 and v2 solvers to represent
 * a piece that has been rotated and placed on the board.
 */
struct RotatedPiece {
    Piece piece;      ///< The piece data (with rotation applied)
    int rotation;     ///< Rotation value (0-3)
    int index;        ///< Original piece index
};

/**
 * @brief 2D board index (x, y coordinates)
 */
using Index = std::pair<size_t, size_t>;

/**
 * @brief Board hash type for duplicate detection
 */
using BoardHash = std::string;

} // namespace eternity2_common

#endif // ETERNITY2_COMMON_TYPES_H

