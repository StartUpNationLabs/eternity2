#define CONFIG_CATCH_MAIN

#include <catch2/catch_all.hpp>
#include "piece/piece.h"
#include "piece_search/piece_search.h"
#include "format/format.h"

const auto pieces = create_pieces_with_availability(std::vector<Piece>{
        make_piece(1, 1, 4, 4),
        make_piece(1, 4, 4, 1),
        make_piece(4, 4, 1, 1),
        make_piece(1, 1, 4, 4)

});

TEST_CASE("Piece mask search", "[Pieces with 4 on the left]") {

    Piece start = make_piece(0, 0, 0, 4);
    Piece mask = LEFT_MASK;
    Query query = {start, mask, QueryType::POSITIVE};
    auto result = match_piece_mask(std::vector<Query>{query}, pieces);
    for (auto r: result) {
        log_piece(r.piece, format("piece: {}", r.rotation));
        Piece rotated_piece = rotate_piece_right(r.piece, r.rotation);
        REQUIRE((rotated_piece & mask) == start);
    }

};

TEST_CASE("Piece mask search2", "[ID: 4 Pieces on Left and Down]") {
    Piece start = make_piece(0, 0, 4, 4);
    Piece mask = LEFT_MASK | DOWN_MASK;
    Query query = {start, mask, QueryType::POSITIVE};
    auto result = match_piece_mask(std::vector<Query>{query}, pieces);
    for (const auto r: result) {
        log_piece(r.piece, format("piece: {}", r.rotation));
        Piece rotated_piece = rotate_piece_right(r.piece, r.rotation);
        REQUIRE((rotated_piece & mask) == start);
    }
    REQUIRE(result.size() == 4);
};

TEST_CASE("Piece mask search3", "[ID: 1 Pieces on Left and Down]") {
    Piece start = make_piece(0, 0, 4, 4);
    Piece mask = LEFT_MASK | DOWN_MASK;
    Query query = {start, mask, QueryType::POSITIVE};
    auto result = match_piece_mask(std::vector<Query>{query}, pieces);
    for (const auto r: result) {
        log_piece(r.piece, format("piece: {}", r.rotation));
        Piece rotated_piece = rotate_piece_right(r.piece, r.rotation);
        REQUIRE((rotated_piece & mask) == start);
    }
    REQUIRE(result.size() == 4);
};