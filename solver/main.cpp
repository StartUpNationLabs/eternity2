#include <iostream>
#include <bitset>
#include <csv.h>
#include "piece/piece.h"
#include "piece_loader/piece_loader.h"




//std::vector<PieceResult> match_piece(PIECE piece1, const std::vector<PIECE> &pieces, int n) {
//    std::cout << "matching piece:" << std::endl;
//    log_piece(piece1);
//    // rotate piece1 to get desired "nth" side to match
//    PIECE piece1_rotated = rotate_piece_right(piece1, n + 2);
//    std::cout << "rotated piece " << n << std::endl;
//    log_piece(piece1_rotated);
//    // make a mask to keep only the side n
//    PIECE mask = get_mask(n);
//    PIECE piece1_masked = piece1_rotated & mask;
//    std::cout << "masked piece " << n << std::endl;
//    log_piece(piece1_masked);
//    return match_piece_mask(piece1_masked, pieces);
//}


int main() {
    std::vector<PIECE> pieces = load_from_csv("file.csv");

    PIECE start = pieces[0];
//    const PIECE test = pieces[0];
//    log_piece(test);
//    auto result = match_piece_mask(test, LEFT_MASK, pieces);
//    for (auto r: result) {
//        log_piece(r.piece);
//        std::cout << "rotation: " << r.rotation << std::endl;
//    }
//    return 0;
}
