#define CONFIG_CATCH_MAIN

#include <catch2/catch_all.hpp>
#include "piece/piece.h"
#include "piece_search/piece_search.h"
#include "spdlog/spdlog.h"

const std::vector<PIECE> pieces = std::vector<PIECE>{
        make_piece(1, 1, 4, 4),
        make_piece(1, 4, 4, 1),
        make_piece(4, 4, 1, 1),
        make_piece(1, 1, 4, 4)

};

TEST_CASE("PIECE mask search", "[Pieces with 4 on the left]") {

    PIECE start = make_piece(0, 0, 0, 4);
    PIECE mask = LEFT_MASK;
    auto result = match_piece_mask(start, mask, pieces);
    for (auto r: result) {
        log_piece(r.piece, fmt::format("piece: {}", r.rotation));
        PIECE rotated_piece = rotate_piece_right(r.piece, r.rotation);
        REQUIRE((rotated_piece & mask) == start);
    };

};

TEST_CASE("PIECE mask search2", "[ID: 4 Pieces on Left and Down]") {
    PIECE start = make_piece(0, 0, 4, 4);
    PIECE mask = LEFT_MASK | DOWN_MASK;
    auto result = match_piece_mask(start, mask, pieces);
    for (auto r: result) {
        log_piece(r.piece, fmt::format("piece: {}", r.rotation));
        PIECE rotated_piece = rotate_piece_right(r.piece, r.rotation);
        REQUIRE((rotated_piece & mask) == start);
    }
    REQUIRE(result.size() == 4);
};
