import json
import re


def parse_source():
    file_path = 'source.txt'
    parsed_data = {"corner": {}, "outer": {}, "normal": {}}

    with open(file_path, 'r') as file:
        for line in file.readlines():
            if not line.startswith('piecesCorner') and \
                    not line.startswith('piecesOuter') and \
                    not line.startswith('piecesNormal'):
                continue
            piece_id = re.findall(r'\d+', line)[0]
            piece_representation = re.findall(r'Piece\(\"([A-Z]{4})\"\)', line)[0]
            if line.startswith('piecesCorner'):
                parsed_data['corner'][piece_id] = piece_representation
            elif line.startswith('piecesOuter'):
                parsed_data['outer'][piece_id] = piece_representation
            elif line.startswith('piecesNormal'):
                parsed_data['normal'][piece_id] = piece_representation

    return parsed_data


if __name__ == '__main__':
    output = {}

    piece_dict = parse_source()
    output['pieces'] = piece_dict

    letter_list = []

    for key in piece_dict:
        for k, v in piece_dict[key].items():
            for letter in v:
                if letter not in letter_list:
                    letter_list.append(letter)

    letter_list.sort()

    output['letters'] = letter_list

    # Save the parsed data to a json
    with open('parsed_data.json', 'w') as file:
        json.dump(output, file)
