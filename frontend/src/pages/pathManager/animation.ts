// Maximum animation duration in milliseconds
export const MAX_ANIMATION_DURATION = 3000; // 3 seconds

// Minimum delay between cells in milliseconds
export const MIN_CELL_DELAY = 30;

/**
 * Calculates the delay between each cell animation based on the path length.
 * Ensures total animation duration never exceeds MAX_ANIMATION_DURATION.
 * 
 * @param pathLength - The number of cells in the path
 * @returns The delay in milliseconds between each cell animation
 */
export const calculateCellDelay = (pathLength: number): number => {
    // Calculate the maximum allowed delay to stay within MAX_ANIMATION_DURATION
    const maxAllowedDelay = Math.floor(MAX_ANIMATION_DURATION / pathLength);
    
    // Base delay of 500ms, scaled down for longer paths
    const baseDelay = 500;
    const scaleFactor = Math.max(1, Math.sqrt(pathLength) / 2);
    const scaledDelay = Math.floor(baseDelay / scaleFactor);
    
    // Return the minimum between scaled delay and max allowed delay, but not less than MIN_CELL_DELAY
    return Math.max(MIN_CELL_DELAY, Math.min(maxAllowedDelay, scaledDelay));
};

/**
 * Calculate the total animation duration based on the number of cells
 * @param totalCells Total number of cells in the path
 * @returns Total animation duration in milliseconds
 */
export const calculateTotalDuration = (totalCells: number): number => {
    const delay = calculateCellDelay(totalCells);
    return Math.min(MAX_ANIMATION_DURATION, delay * totalCells);
}; 