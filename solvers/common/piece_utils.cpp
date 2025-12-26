//
// Common piece utility functions implementation
//

#include "piece_utils.h"

namespace eternity2_common {

Piece make_piece(PiecePart top, PiecePart right, PiecePart down, PiecePart left)
{
    // Concatenate the 4 parts into a single 64-bit integer
    // Look at the MASKs to understand the order of the parts
    return static_cast<Piece>(left) | (static_cast<Piece>(down) << 16U) | (static_cast<Piece>(right) << 32U)
           | (static_cast<Piece>(top) << 48U);
}

Piece rotate_piece_right(Piece piece, int n)
{
    if (n == 0)
    {
        return piece;
    }
    // Rotate the piece n times
    Piece rotated_piece = piece >> (16U * n);
    // Add the bits that were shifted out to the beginning
    rotated_piece |= piece << (64U - 16U * n);
    return rotated_piece;
}

Piece rotate_piece_left(Piece piece, int n)
{
    if (n == 0)
    {
        return piece;
    }
    // Rotate the piece n times
    Piece rotated_piece = piece << (16U * n);
    // Add the bits that were shifted out to the end
    rotated_piece |= piece >> (64U - 16U * n);
    return rotated_piece;
}

PiecePart get_piece_part(Piece piece, Piece mask)
{
    // Get the part of the piece
    // Use the MASKs to extract the part from the piece and shift it to the right position
    return static_cast<PiecePart>((piece & mask) >> (mask == UP_MASK      ? 48U
                                                     : mask == RIGHT_MASK ? 32U
                                                                          : (mask == DOWN_MASK ? 16U : 0U)));
}

} // namespace eternity2_common

