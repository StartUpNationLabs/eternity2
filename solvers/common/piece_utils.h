//
// Common piece utility functions shared between solver versions
//

#ifndef ETERNITY2_COMMON_PIECE_UTILS_H
#define ETERNITY2_COMMON_PIECE_UTILS_H

#include "types.h"
#include <vector>

namespace eternity2_common {

/**
 * @brief Create a piece from four parts (top, right, bottom, left)
 * 
 * @param top Top edge value
 * @param right Right edge value
 * @param down Bottom edge value
 * @param left Left edge value
 * @return Piece The combined piece value
 */
Piece make_piece(PiecePart top, PiecePart right, PiecePart down, PiecePart left);

/**
 * @brief Rotate a piece right (clockwise) n times
 * 
 * @param piece The piece to rotate
 * @param n Number of rotations (0-3)
 * @return Piece The rotated piece
 */
Piece rotate_piece_right(Piece piece, int n);

/**
 * @brief Rotate a piece left (counter-clockwise) n times
 * 
 * @param piece The piece to rotate
 * @param n Number of rotations (0-3)
 * @return Piece The rotated piece
 */
Piece rotate_piece_left(Piece piece, int n);

/**
 * @brief Extract a specific part from a piece using a mask
 * 
 * @param piece The piece to extract from
 * @param mask The mask to use (UP_MASK, RIGHT_MASK, DOWN_MASK, or LEFT_MASK)
 * @return PiecePart The extracted part value
 */
PiecePart get_piece_part(Piece piece, Piece mask);

} // namespace eternity2_common

#endif // ETERNITY2_COMMON_PIECE_UTILS_H

