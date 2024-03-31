import {useCallback, useEffect, useState} from 'react';
import {useRecoilState} from "recoil";
import {boardSizeState, displayedCellsState, selectedCellsState} from "./atom.ts";

enum Movement {
    Up = 'up',
    Down = 'down',
    Left = 'left',
    Right = 'right',
    UpLeft = 'up-left',
    UpRight = 'up-right',
    DownLeft = 'down-left',
    DownRight = 'down-right'
}

function PathManagerGrid() {
    // States used to manage path manager
    const boardSize = useRecoilState(boardSizeState)[0];
    const [displayedCells, setDisplayedCells] = useRecoilState(displayedCellsState);
    const [selectedCells, setSelectedCells] = useRecoilState(selectedCellsState);

    // States used to handle cell selection
    const [isMouseDown, setIsMouseDown] = useState<boolean>(false); // State to track mouse button press
    const [initialCellId, setInitialCellId] = useState<number | null>(null); // State to store initial cell id when mouse down
    const [lastSelectedCellId, setLastSelectedCellId] = useState<number | null>(null);

    // Function to handle cell selection
    const handleCellClick = useCallback((id: number) => {
        if (!isMouseDown) {
            // ID 0 is the default cell, which should not be selected
            if (selectedCells.includes(id) && id !== 0) {
                // Deselect cell if already selected
                setSelectedCells(selectedCells.filter(cell => cell !== id));
                setDisplayedCells(displayedCells.filter(cell => cell !== id));
            } else {
                if (id !== 0) {
                    setSelectedCells([...selectedCells, id]);
                    setDisplayedCells([...displayedCells, id]);
                }
            }
        }
    }, [isMouseDown, selectedCells, setSelectedCells]);

    useEffect(() => {
        // Add event listeners when component mounts
        const handleMouseUp = () => {
            if (isMouseDown && initialCellId === lastSelectedCellId) {
                // Treat as single click if mouse didn't move
                if (initialCellId !== null) {
                    handleCellClick(initialCellId);
                }
            }
            setIsMouseDown(false);
            setInitialCellId(null);
            setLastSelectedCellId(null);
        };

        window.addEventListener('mouseup', handleMouseUp);

        // Cleanup event listeners when component unmounts
        return () => {
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isMouseDown, initialCellId, lastSelectedCellId, handleCellClick]);

    // Function to calculate direction of selection based on current and last cell id
    const calculateDirection = (currentCellId: number, lastCellId: number | null): Movement | null => {
        if (lastCellId === null) return null;

        const rowDiff = Math.floor(currentCellId / boardSize) - Math.floor(lastCellId / boardSize);
        const colDiff = currentCellId % boardSize - lastCellId % boardSize;
        if (rowDiff === -1 && colDiff === 0) return Movement.Up;
        if (rowDiff === 1 && colDiff === 0) return Movement.Down;
        if (rowDiff === 0 && colDiff === -1) return Movement.Left;
        if (rowDiff === 0 && colDiff === 1) return Movement.Right;
        if (rowDiff === -1 && colDiff === -1) return Movement.UpLeft;
        if (rowDiff === -1 && colDiff === 1) return Movement.UpRight;
        if (rowDiff === 1 && colDiff === -1) return Movement.DownLeft;
        if (rowDiff === 1 && colDiff === 1) return Movement.DownRight;

        return null;
    };

    const handleCellSelection = (id: number) => {
        if (isMouseDown) {
            if (initialCellId === null) {
                setInitialCellId(id);
                setLastSelectedCellId(id);
                setSelectedCells([id]);
            } else {
                const direction = calculateDirection(id, lastSelectedCellId);
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
                    setDisplayedCells(uniqueSelectedCells);
                    setLastSelectedCellId(id);
                }
            }
        }
    };

    const renderGrid = () => {
        const cells = [];

        for (let i = 0; i < boardSize; i++) {
            for (let j = 0; j < boardSize; j++) {
                const id = i * boardSize + j; // Calculate cell id
                const rank = displayedCells.indexOf(id);
                cells.push(
                    {
                        id: id,
                        rank: rank,
                    }
                );
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
                                backgroundColor: cell.rank !== -1 ? rankToColor(cell.rank) : '#bbbbbb',
                                display: 'flex',
                                position: 'relative',
                                width: '100%',
                                height: '100%',
                                aspectRatio: 1,
                                boxShadow: "inset 0 0 0 1px black",
                                cursor: "pointer",
                                fontSize: "12px",
                            }}
                            onMouseDown={() => {
                                setIsMouseDown(true);
                                setInitialCellId(cell.id);
                                setLastSelectedCellId(cell.id);
                                handleCellClick(cell.id); // Handle single click
                            }}
                            onMouseEnter={() => {
                                handleCellSelection(cell.id); // Handle click-and-drag selection
                            }}
                        >
                            {cell.rank !== -1 && <span style={{
                                position: "absolute",
                                top: "50%",
                                left: "50%",
                                transform: "translate(-50%, -50%)",
                                userSelect: "none"
                            }}>{cell.rank}</span>}
                        </div>
                    ))}
                </div>

            </div>
        );
    }

    // Function to map rank to color gradient between dark blue and light blue (excluding 10% at both ends)
    const rankToColor = (rank: number) => {
        const limitPercentage = 0.8;
        const numberOfSteps = boardSize * boardSize;
        const baseColorR = Math.floor(255 * limitPercentage);
        const baseColorG = 0;
        const baseColorB = 0;

        // Adjust the range to exclude the extreme 10% colors
        const adjustedRange = 255 * 0.1 * (numberOfSteps / (numberOfSteps - 2));

        // Only range across blue and red
        const colorR = Math.floor(baseColorR - (baseColorR * rank / numberOfSteps) - adjustedRange);
        const colorG = Math.floor(baseColorG + (255 * rank / numberOfSteps) - adjustedRange);
        const colorB = Math.floor(baseColorB + (255 * rank / numberOfSteps) - adjustedRange);

        return `rgb(${colorR}, ${colorG}, ${colorB})`;
    };

    return (
        <div>
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                width: '100%',
                height: '100%',
                margin: 'auto',
            }}>
                {renderGrid()}
            </div>
        </div>
    );
}

export default PathManagerGrid;
