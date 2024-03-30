import {useEffect, useRef, useState} from 'react';
import './GridSelector.css';
import {red} from "@mui/material/colors"; // Style file for the component

function GridSelector() {
    const [gridSize, setGridSize] = useState(5); // Initial grid size
    const [selectedCells, setSelectedCells] = useState([]); // Array to hold selected cells
    const [cellCounter, setCellCounter] = useState(0); // Counter for displaying rank in selected cells
    const [isMouseDown, setIsMouseDown] = useState(false); // State to track mouse button press
    const [initialCellId, setInitialCellId] = useState(null); // State to store initial cell id when mouse down
    const [lastSelectedCellId, setLastSelectedCellId] = useState(null); // State to store last selected cell id
    const gridRef = useRef(null); // Ref to grid container

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
    const calculateDirection = (currentCellId, lastCellId) => {
        const rowDiff = Math.floor(currentCellId / gridSize) - Math.floor(lastCellId / gridSize);
        const colDiff = currentCellId % gridSize - lastCellId % gridSize;

        if (rowDiff === -1 && colDiff === 0) return 'up';
        if (rowDiff === 1 && colDiff === 0) return 'down';
        if (rowDiff === 0 && colDiff === -1) return 'left';
        if (rowDiff === 0 && colDiff === 1) return 'right';

        return null;
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
                const direction = calculateDirection(id, lastSelectedCellId);
                const selectedRange = [];

                if (direction) {
                    // Calculate cells between lastSelectedCellId and current cell id based on direction
                    let currentId = lastSelectedCellId;
                    while (currentId !== id) {
                        selectedRange.push(currentId);
                        switch (direction) {
                            case 'up':
                                currentId -= gridSize;
                                break;
                            case 'down':
                                currentId += gridSize;
                                break;
                            case 'left':
                                currentId -= 1;
                                break;
                            case 'right':
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

    // Function to generate grid based on gridSize
    const renderGrid = () => {
        const grid = [];
        for (let i = 0; i < gridSize; i++) {
            for (let j = 0; j < gridSize; j++) {
                const id = i * gridSize + j; // Calculate cell id
                const rank = selectedCells.indexOf(id);
                const backgroundColor = rank !== -1 ? rankToColor(rank) : 'white';
                grid.push(
                    <div
                        key={id}
                        className="grid-cell"
                        style={{backgroundColor}}
                        onMouseDown={() => {
                            setIsMouseDown(true);
                            setInitialCellId(id);
                            setLastSelectedCellId(id);
                            handleCellClick(id); // Handle single click
                        }}
                        onMouseEnter={() => {
                            handleCellSelection(id); // Handle click-and-drag selection
                        }}
                    >
                        {rank !== -1 && <span className="cell-rank">{rank}</span>}
                    </div>
                );
            }
        }
        return grid;
    };

    // Function to map rank to color gradient between dark blue and light blue (excluding 10% at both ends)
    const rankToColor = (rank) => {
        const limitPercentage = 0.8;
        const numberOfSteps = gridSize * gridSize;
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
        setGridSize(newSize);
        setSelectedCells([]); // Clear selected cells when grid size changes
        setCellCounter(0); // Reset cell counter
    };

    // Function to generate slider for grid size
    const renderSlider = () => {
        return (
            <div className="slider-container">
                <label htmlFor="grid-size-slider">Grid Size:</label>
                <input
                    type="range"
                    id="grid-size-slider"
                    name="grid-size-slider"
                    min="3"
                    max="10"
                    value={gridSize}
                    onChange={handleSliderChange}
                />
                <span>{gridSize}</span>
            </div>
        );
    };

    return (
        <div className="grid-container">
            {renderSlider()}
            <div className="grid" ref={gridRef} style={{gridTemplateColumns: `repeat(${gridSize}, minmax(30px, 1fr))`}}>
                {renderGrid()}
            </div>
            <div className="controls">
                <button onClick={handleReset}>Reset</button>
            </div>
            <div className="selected-cell-ids">
                <h3>Selected Cell IDs:</h3>
                <p>{renderSelectedCellIds().join(', ')}</p>
            </div>
        </div>
    );
}

export default GridSelector;
