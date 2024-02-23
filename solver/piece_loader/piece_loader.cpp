//
// Created by appad on 10/02/2024.
//

#include <fstream>
#include "piece_loader.h"


std::vector<Piece> load_from_csv(const std::string &filename) {
    // function to load pieces from a csv file
    // the csv file should contain the bit strings of the pieces
    // the bit strings are converted to Piece and returned as a vector

    std::ifstream in(filename);

    std::vector<Piece> pieces = {};
    while (in.good()) {
        std::string line;
        std::getline(in, line);
        if (line.empty()) {
            continue;
        }
        std::string a;
        std::string b;
        std::string c;
        std::string d;
        // split the line by comma
        a = line.substr(0, line.find(','));
        line = line.substr(line.find(',') + 1);
        b = line.substr(0, line.find(','));
        line = line.substr(line.find(',') + 1);
        c = line.substr(0, line.find(','));
        line = line.substr(line.find(',') + 1);
        d = line;


        // read bit strings from csv and convert them to Piece
        auto as = (PiecePart) strtol(a.c_str(), nullptr, 2);
        auto bs = (PiecePart) strtol(b.c_str(), nullptr, 2);
        auto cs = (PiecePart) strtol(c.c_str(), nullptr, 2);
        auto ds = (PiecePart) strtol(d.c_str(), nullptr, 2);

        Piece piece = make_piece(as, bs, cs, ds);
        pieces.push_back(piece);
    }
    return pieces;
}

std::vector<Piece> load_from_csv_string(std::string &csv_string) {
    // function to load pieces from a csv string
    // the csv string should contain the bit strings of the pieces
    // the bit strings are converted to Piece and returned as a vector

    // iterate over the lines of the csv string
    std::vector<Piece> pieces;
    std::string delimiter = "\n";
    size_t pos = 0;
    std::string token;

    while ((pos = csv_string.find(delimiter)) != std::string::npos) {
        token = csv_string.substr(0, pos);
        std::string a;
        std::string b;
        std::string c;
        std::string d;
        // split the line by comma
        a = token.substr(0, token.find(','));
        token = token.substr(token.find(',') + 1);
        b = token.substr(0, token.find(','));
        token = token.substr(token.find(',') + 1);
        c = token.substr(0, token.find(','));
        token = token.substr(token.find(',') + 1);
        d = token;

        // read bit strings from csv and convert them to Piece
        auto as = (PiecePart) strtol(a.c_str(), nullptr, 2);
        auto bs = (PiecePart) strtol(b.c_str(), nullptr, 2);
        auto cs = (PiecePart) strtol(c.c_str(), nullptr, 2);
        auto ds = (PiecePart) strtol(d.c_str(), nullptr, 2);

        Piece piece = make_piece(as, bs, cs, ds);
        pieces.push_back(piece);
        csv_string.erase(0, pos + delimiter.length());
    }
    return pieces;
}