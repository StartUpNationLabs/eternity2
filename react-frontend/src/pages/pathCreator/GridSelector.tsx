import React, {useEffect, useState} from 'react';
import {gridSelectorState} from "../requestForm/atoms.ts";
import {useRecoilState} from "recoil";

function GridSelector() {
    const [gridSelector, setGridSelector] = useRecoilState(gridSelectorState);
    const [isMouseDown, setIsMouseDown] = useState(false); // State to track mouse button press
    const [initialCellId, setInitialCellId] = useState(null); // State to store initial cell id when mouse down
    const [lastSelectedCellId, setLastSelectedCellId] = useState(null); // State to store last selected cell id

    console.log(gridSelector.selectedCells.length)
    console.log(gridSelector.selectedCells)

    const boardSize = gridSelector.boardSize;
    const setBoardSize = function (boardSize: number) {
        setGridSelector({
            ...gridSelector,
            boardSize: boardSize
        })
    }

    const selectedCells = gridSelector.selectedCells;
    const setSelectedCells = function (selectedCells: number[]) {
        setGridSelector({
            ...gridSelector,
            selectedCells: selectedCells
        })
    }

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
        if (rowDiff === -1 && colDiff === 0) return 'up';
        if (rowDiff === 1 && colDiff === 0) return 'down';
        if (rowDiff === 0 && colDiff === -1) return 'left';
        if (rowDiff === 0 && colDiff === 1) return 'right';
        if (rowDiff === -1 && colDiff === -1) return 'up-left';
        if (rowDiff === -1 && colDiff === 1) return 'up-right';
        if (rowDiff === 1 && colDiff === -1) return 'down-left';
        if (rowDiff === 1 && colDiff === 1) return 'down-right';

        return null;
    };

    // Function to handle cell selection
    const handleCellClick = (id: number) => {
        if (!isMouseDown) {
            if (selectedCells.includes(id)) {
                // Deselect cell if already selected
                setSelectedCells(selectedCells.filter(cell => cell !== id));
            } else {
                setSelectedCells([...selectedCells, id]);
            }
        }
    };

    const handleCellSelection = (id: number) => {
        if (isMouseDown) {
            if (initialCellId === null) {
                // Set initial cell id when mouse down
                setInitialCellId(id);
                setLastSelectedCellId(id);
                setSelectedCells([id]);
            } else {
                const direction = calculateDirection(id, lastSelectedCellId);
                const selectedRange = [];

                if (direction) {
                    // Calculate cells between lastSelectedCellId and current cell id based on direction
                    let currentId = lastSelectedCellId;
                    while (currentId !== id) {
                        selectedRange.push(currentId);
                        switch (direction) {
                            case 'up':
                                currentId -= boardSize;
                                break;
                            case 'down':
                                currentId += boardSize;
                                break;
                            case 'left':
                                currentId -= 1;
                                break;
                            case 'right':
                                currentId += 1;
                                break;
                            case 'up-left':
                                currentId -= boardSize + 1;
                                break;
                            case 'up-right':
                                currentId -= boardSize - 1;
                                break;
                            case 'down-left':
                                currentId += boardSize - 1;
                                break;
                            case 'down-right':
                                currentId += boardSize + 1;
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

    // Function to handle slider change
    const handleSliderChange = (event) => {
        const newSize = parseInt(event.target.value);
        setBoardSize(newSize);
        setSelectedCells([]); // Clear selected cells when grid size changes
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
