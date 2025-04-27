import {useCallback, useState} from 'react';
import {useRecoilState} from "recoil";
import {boardSizeState, hintCellsState, selectedCellsState} from "./atom.ts";
import {calculateDirection, Movement, rankToColor} from "./utils.ts";

function PathManagerGrid() {
    // States used to manage path manager
    const boardSize = useRecoilState(boardSizeState)[0];
    const [selectedCells, setSelectedCells] = useRecoilState(selectedCellsState);
    const [hintCells, setHintCells] = useRecoilState(hintCellsState);

    // States used to handle cell selection
    const [isMouseDown, setIsMouseDown] = useState<boolean>(false);
    const [initialCellId, setInitialCellId] = useState<number | null>(null);
    const [lastSelectedCellId, setLastSelectedCellId] = useState<number | null>(null);

    // Function to handle cell selection
    const handleCellClick = useCallback((id: number) => {
        // Do not allow selection of hint cells
        if (hintCells.includes(id)) return;

        // Set initial cell id and last selected cell id
        setIsMouseDown(true);
        setInitialCellId(id);
        setLastSelectedCellId(id);

        // Handle cell selection
        if (!isMouseDown) {
            // ID 0 is the default cell, which should not be selected
            if (selectedCells.includes(id) && id !== 0) {
                // Deselect cell if already selected
                setSelectedCells(selectedCells.filter(cell => cell !== id));
            } else {
                if (id !== 0) {
                    setSelectedCells([...selectedCells, id]);
                }
            }
        }
    }, [hintCells, isMouseDown, selectedCells, setSelectedCells]);

    // Function to handle cell right click
    const handleCellRightClick = (id: number) => {
        if (!hintCells.includes(id)) {
            setHintCells([...hintCells, id]); // Add cell id to hintCells
            if (!selectedCells.includes(id)) {
                setSelectedCells([...selectedCells, id]); // Add cell id to selectedCells only if it's not already there
            }
        } else {
            setHintCells(hintCells.filter((hintCell) => hintCell !== id)); // Remove cell id from hintCells
            setSelectedCells(selectedCells.filter((selectedCell) => selectedCell !== id)); // Remove cell id from selectedCells
        }
    }

    // Function to handle cell selection when mouse is dragged
    const handleCellSelection = (id: number) => {
        if (isMouseDown) {
            if (initialCellId === null) {
                setInitialCellId(id);
                setLastSelectedCellId(id);
                setSelectedCells([id]);
            } else {
                const direction = calculateDirection(boardSize, id, lastSelectedCellId);
                const selectedRange = [];

                if (direction) {
                    let currentId: number | null = lastSelectedCellId;
                    while (currentId !== null && currentId !== id) {
                        selectedRange.push(currentId);
                        switch (direction) {
                            case Movement.Up:
                                currentId -= boardSize;
                                break;
                            case Movement.Down:
                                currentId += boardSize;
                                break;
                            case Movement.Left:
                                currentId -= 1;
                                break;
                            case Movement.Right:
                                currentId += 1;
                                break;
                            case Movement.UpLeft:
                                currentId -= boardSize + 1;
                                break;
                            case Movement.UpRight:
                                currentId -= boardSize - 1;
                                break;
                            case Movement.DownLeft:
                                currentId += boardSize - 1;
                                break;
                            case Movement.DownRight:
                                currentId += boardSize + 1;
                                break;
                            default:
                                break;
                        }
                    }
                }

                if (selectedRange.length > 0) {
                    const newSelectedCells = [...selectedCells, ...selectedRange, id];
                    const uniqueSelectedCells = newSelectedCells.filter((cell, index, array) => array.indexOf(cell) === index);
                    setSelectedCells(uniqueSelectedCells);
                    setLastSelectedCellId(id);
                }
            }
        }
    };

    const handleMouseUp = () => {
        setIsMouseDown(false);
        setInitialCellId(null);
        setLastSelectedCellId(null);
    };

    const renderGrid = () => {
        const cells = [];

        for (let i = 0; i < boardSize; i++) {
            for (let j = 0; j < boardSize; j++) {
                const id = i * boardSize + j;
                const rank = selectedCells.indexOf(id);
                
                cells.push({
                    id,
                    rank,
                });
            }
        }

        return (
            <div style={{width: "100%"}}>
                <div
                    style={{
                        display: "grid",
                        gridTemplateColumns: `repeat(${boardSize}, 1fr)`,
                        gridTemplateRows: `repeat(${boardSize}, 1fr)`,
                        gap: '0px',
                    }}
                >
                    {cells.map((cell) => (
                        <div
                            key={cell.id}
                            style={{
                                backgroundColor: hintCells.includes(cell.id) 
                                    ? 'green' 
                                    : (cell.rank !== -1 
                                        ? rankToColor(boardSize, cell.rank)
                                        : '#9a9a9a'),
                                display: 'flex',
                                justifyContent: 'center',
                                alignItems: 'center',
                                aspectRatio: '1/1',
                                cursor: 'pointer',
                                userSelect: 'none',
                                border: '1px solid #000',
                            }}
                            onMouseDown={() => handleCellClick(cell.id)}
                            onMouseEnter={() => handleCellSelection(cell.id)}
                            onMouseUp={handleMouseUp}
                            onContextMenu={(e) => {
                                e.preventDefault();
                                handleCellRightClick(cell.id);
                            }}
                        >
                            {cell.rank !== -1 && cell.rank + 1}
                        </div>
                    ))}
                </div>
            </div>
        );
    };

    return renderGrid();
}

export default PathManagerGrid;
