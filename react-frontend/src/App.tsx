import { useState } from 'react';
import Board from './Board';

function App() {
    const [size, setSize] = useState(5);
    const [numberOfSymbols, setNumberOfSymbols] = useState(5);

    return (
        <div>
            <h1>Eternity II Puzzle Generator</h1>
            <div>
                <label>Board Size: {size}x{size}</label>
                <input type="range" min="3" max="10" value={size} onChange={e => setSize(Number(e.target.value))} />
            </div>
            <div>
                <label>Number of Symbols: {numberOfSymbols}</label>
                <input type="range" min="1" max="30" value={numberOfSymbols} onChange={e => setNumberOfSymbols(Number(e.target.value))} />
            </div>
            <Board size={size} numberOfSymbols={numberOfSymbols} />
        </div>
    );
}

export default App;
