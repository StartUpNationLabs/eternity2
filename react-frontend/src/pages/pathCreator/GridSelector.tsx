import React, {useEffect, useState} from 'react';
import {Direction} from "../../utils/Constants.tsx";

function GridSelector() {
    const [boardSize, setBoardSize] = useState(5); // Initial grid size
    const [selectedCells, setSelectedCells] = useState([]); // Array to hold selected cells
    const [cellCounter, setCellCounter] = useState(0); // Counter for displaying rank in selected cells
    const [isMouseDown, setIsMouseDown] = useState(false); // State to track mouse button press
    const [initialCellId, setInitialCellId] = useState(null); // State to store initial cell id when mouse down
    const [lastSelectedCellId, setLastSelectedCellId] = useState(null); // State to store last selected cell id

    useEffect(() => {
        // Add event listeners when component mounts
        const handleMouseUp = () => {
            if (isMouseDown && initialCellId === lastSelectedCellId) {
                // Treat as single click if mouse didn't move
                handleCellClick(initialCellId);
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
    }, [isMouseDown, initialCellId, lastSelectedCellId]);

    // Function to calculate the direction of selection based on movement
    const calculateDirection = (currentCellId: number, lastCellId: number) => {
        const rowDiff = Math.floor(currentCellId / boardSize) - Math.floor(lastCellId / boardSize);
        const colDiff = currentCellId % boardSize - lastCellId % boardSize;

        if (rowDiff === -1 && colDiff === 0) return Direction.Top;
        else if (rowDiff === 1 && colDiff === 0) return Direction.Bottom;
        else if (rowDiff === 0 && colDiff === -1) return Direction.Left;
        else (rowDiff === 0 && colDiff === 1)
        return Direction.Right;
    };

    // Function to handle cell selection
    const handleCellClick = (id) => {
        if (!isMouseDown) {
            if (selectedCells.includes(id)) {
                // Deselect cell if already selected
                setSelectedCells(selectedCells.filter(cell => cell !== id));
            } else {
                // Select cell and increment rank
                setSelectedCells([...selectedCells, id]);
                setCellCounter(cellCounter + 1);
            }
        }
    };

    // Function to handle click-and-drag selection
    const handleCellSelection = (id) => {
        if (isMouseDown) {
            if (initialCellId === null) {
                // Set initial cell id when mouse down
                setInitialCellId(id);
                setLastSelectedCellId(id);
                setSelectedCells([id]);
            } else {
                const direction: Direction = calculateDirection(id, lastSelectedCellId);
                const selectedRange = [];

                if (direction) {
                    // Calculate cells between lastSelectedCellId and current cell id based on direction
                    let currentId = lastSelectedCellId;
                    while (currentId !== id) {
                        selectedRange.push(currentId);
                        switch (direction) {
                            case Direction.Top:
                                currentId -= boardSize;
                                break;
                            case Direction.Bottom:
                                currentId += boardSize;
                                break;
                            case Direction.Left:
                                currentId -= 1;
                                break;
                            case Direction.Right:
                                currentId += 1;
                                break;
                            default:
                                break;
                        }
                    }
                }

                if (selectedRange.length > 0) {
                    const newSelectedCells = [...selectedCells, ...selectedRange, id];
                    setSelectedCells(newSelectedCells.filter((cell, index, array) => array.indexOf(cell) === index)); // Remove duplicates
                    setLastSelectedCellId(id);
                }
            }
        }
    };

    // Function to reset the grid
    const handleReset = () => {
        setSelectedCells([]);
        setCellCounter(0);
    };

    const renderGrid = () => {
        const cells = [];

        for (let i = 0; i < boardSize; i++) {
            for (let j = 0; j < boardSize; j++) {
                const id = i * boardSize + j; // Calculate cell id
                const rank = selectedCells.indexOf(id);
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
                                backgroundColor: cell.rank !== -1 ? rankToColor(cell.rank) : 'white',
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
    const rankToColor = (rank) => {
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

    // Function to generate list of selected cell ids ordered by their ranking
    const renderSelectedCellIds = () => {
        return selectedCells;
    };

    // Function to handle slider change
    const handleSliderChange = (event) => {
        const newSize = parseInt(event.target.value);
        setBoardSize(newSize);
        setSelectedCells([]); // Clear selected cells when grid size changes
        setCellCounter(0); // Reset cell counter
    };

    // Function to generate slider for grid size
    const renderSlider = () => {
        return (
            <div>
                <label htmlFor="grid-size-slider">Grid Size:</label>
                <input
                    type="range"
                    id="grid-size-slider"
                    name="grid-size-slider"
                    min="2"
                    max="16"
                    value={boardSize}
                    onChange={handleSliderChange}
                />
                <span>{boardSize}</span>
            </div>
        );
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

export default GridSelector;
