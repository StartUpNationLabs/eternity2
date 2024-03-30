import React, {useEffect, useRef, useState} from 'react';
import './GridSelector.css'; // Style file for the component

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
                let selectedRange = [];

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
        const minRank = gridSize * gridSize * 0.2; // Exclude 10% of the darkest colors
        const maxRank = gridSize * gridSize * 0.8; // Exclude 10% of the lightest colors
        const adjustedRank = Math.max(minRank, Math.min(maxRank, rank));
        const ratio = (adjustedRank - minRank) / (maxRank - minRank);
        const r = Math.round(0 + ratio * (255 - 0)); // Adjust the range for the red component (0 to 255)
        const g = Math.round(0 + ratio * (255 - 0)); // Adjust the range for the green component (0 to 255)
        const b = Math.round(139 + ratio * (255 - 139)); // Adjust the range for the blue component (139 to 255)
        return `rgb(${r}, ${g}, ${b})`;
    };

    // Function to generate list of selected cell ids ordered by their ranking
    const renderSelectedCellIds = () => {
        const orderedCellIds = selectedCells.map(id => `[${id % gridSize},${Math.floor(id / gridSize)}]`).sort();
        return orderedCellIds;
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
