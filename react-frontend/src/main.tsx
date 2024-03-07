import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import {CssBaseline, ThemeProvider} from "@mui/material";
import theme from "./theme.tsx";

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <ThemeProvider theme={theme}>
            <App/>
            <CssBaseline/>
        </ThemeProvider>
    </React.StrictMode>,
)
