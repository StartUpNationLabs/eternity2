import React from "react";

export function useStateHistory<T>(
    initialValue?: T | (() => T)
): [T | undefined, (state: T) => void, Array<T>] {
    const [allStates, setState] = React.useReducer(
        (oldState: T[], newState: T) => {
            return [...oldState, newState];
        },
        typeof initialValue === "function"
            ? [(initialValue as () => T)()]
            : initialValue !== undefined
                ? [initialValue as T]
                : []
    );

    const currentState = allStates[allStates.length - 1];
    const stateHistory = allStates.slice(0, allStates.length - 1);
    return [currentState, setState, stateHistory];
}