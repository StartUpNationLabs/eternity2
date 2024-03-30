import * as React from 'react';
import { styled, createTheme, ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import MuiDrawer from '@mui/material/Drawer';
import Box from '@mui/material/Box';
import MuiAppBar, { AppBarProps as MuiAppBarProps } from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import List from '@mui/material/List';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import Badge from '@mui/material/Badge';
import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import MenuIcon from '@mui/icons-material/Menu';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import { mainListItems, secondaryListItems } from './listItems';
import {useEffect, useState} from "react";
import {createBoard, PieceData, rotatePiece, shuffleAndRotateBoard} from "./logic.tsx";
import {GrpcWebFetchTransport} from "@protobuf-ts/grpcweb-transport";
import {SolverClient} from "./proto/solver/v1/solver.client.ts";
import {Button, Slider} from "@mui/material";
import Piece from "./Piece.tsx";
import Paper from "@mui/material/Paper";

const drawerWidth: number = 240;

interface AppBarProps extends MuiAppBarProps {
    open?: boolean;
}
export default function Dashboard() {
    const [open, setOpen] = React.useState(true);
    const [size, setSize] = useState(5);
    const [symbols, setSymbols] = useState(5);
    const [timer, setTimer] = useState(0);
    const [timerActive, setTimerActive] = useState(false);
    const [board, setBoard] = useState<PieceData[][]>([]);
    const [shuffledBoard, setShuffledBoard] = useState<PieceData[][]>([]);
    const [resolvedBoard, setResolvedBoard] = useState<PieceData[][]>([]); // New state for the resolved board
    const [shouldResolve, setShouldResolve] = useState(false); // Nouvel état pour contrôler le lancement de la résolution


    const AppBar = styled(MuiAppBar, {
        shouldForwardProp: (prop) => prop !== 'open',
    })<AppBarProps>(({ theme, open }) => ({
        zIndex: theme.zIndex.drawer + 1,
        transition: theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
        }),
        ...(open && {
            marginLeft: drawerWidth,
            width: `calc(100% - ${drawerWidth}px)`,
            transition: theme.transitions.create(['width', 'margin'], {
                easing: theme.transitions.easing.sharp,
                duration: theme.transitions.duration.enteringScreen,
            }),
        }),
    }));

    const Drawer = styled(MuiDrawer, { shouldForwardProp: (prop) => prop !== 'open' })(
        ({ theme, open }) => ({
            '& .MuiDrawer-paper': {
                position: 'relative',
                whiteSpace: 'nowrap',
                width: drawerWidth,
                transition: theme.transitions.create('width', {
                    easing: theme.transitions.easing.sharp,
                    duration: theme.transitions.duration.enteringScreen,
                }),
                boxSizing: 'border-box',
                ...(!open && {
                    overflowX: 'hidden',
                    transition: theme.transitions.create('width', {
                        easing: theme.transitions.easing.sharp,
                        duration: theme.transitions.duration.leavingScreen,
                    }),
                    width: theme.spacing(7),
                    [theme.breakpoints.up('sm')]: {
                        width: theme.spacing(9),
                    },
                }),
            },
        }),
    );
    const defaultTheme = createTheme();
    const resolveAndDisplayBoard = async () => {
        setTimerActive(true);
        const transport = new GrpcWebFetchTransport({
            baseUrl: "http://node-apoorva3-abklev50.k3s.hs.ozeliurs.com:50052",
            format: "binary",
        });
        const solverClient = new SolverClient(transport);
        const pieces = shuffledBoard.flat().map(({ top, right, bottom, left }) => ({
            top: top === "0".repeat(16) ? 65535 : parseInt(top, 2),
            right: right === "0".repeat(16) ? 65535 : parseInt(right, 2),
            bottom: bottom === "0".repeat(16) ? 65535 : parseInt(bottom, 2),
            left: left === "0".repeat(16) ? 65535 : parseInt(left, 2),
        }));

        const stream = solverClient.solveStepByStep({
            pieces: pieces,
            threads: 4,
            hashThreshold: 4,
            waitTime: 1,
        });

        for await (const message of stream.responses) {
            console.log("Message de résolution reçu:", message);
            const resolvedPieces = message.rotatedPieces.map(({ piece, rotation }) => {
                let rotatedPiece = {
                    top: piece.top === 65535 ? "0000000000000000" : piece.top.toString(2).padStart(16, '0'),
                    right: piece.right === 65535 ? "0000000000000000" : piece.right.toString(2).padStart(16, '0'),
                    bottom: piece.bottom === 65535 ? "0000000000000000" : piece.bottom.toString(2).padStart(16, '0'),
                    left: piece.left === 65535 ? "0000000000000000" : piece.left.toString(2).padStart(16, '0'),
                };
                rotatedPiece = rotatePiece(rotatedPiece, rotation);
                setTimeout(() => {
                },1000);
                return rotatedPiece;
            });

            setResolvedBoard(resolvedPieces.reduce((acc, curr, index) => {
                const row = Math.floor(index / size);
                if (!acc[row]) acc[row] = [];
                acc[row].push(curr);
                return acc;
            }, []));
        }
        setTimerActive(false)
    };
    const handleStart = async () => {
        setShouldResolve(false);

        const generatedBoard = createBoard(size, symbols);
        setBoard(generatedBoard);

        const shuffled = shuffleAndRotateBoard([...generatedBoard]);
        setShuffledBoard(shuffled);
        setTimeout(() => {
            setShouldResolve(true);
        }, 1000);
    };


    const handleReset = () => {
        setTimer(0);
        setTimerActive(false);
        setShouldResolve(false);
        setBoard([]);
        setShuffledBoard([]);
        setResolvedBoard([]);
    };

    useEffect(() => {
        const newBoard = createBoard(size, symbols);
        setBoard(newBoard);
    }, [size, symbols]);

    useEffect(() => {
        if (shouldResolve) {
            resolveAndDisplayBoard();
        }
    }, [shouldResolve]);
    useEffect(() => {
        if (timerActive) {
            const interval = setInterval(() => setTimer(prev => prev + 1), 1000);
            return () => clearInterval(interval);
        }
    }, [timerActive]);

    const toggleDrawer = () => {
        setOpen(!open);
    };

    return (
        <ThemeProvider theme={defaultTheme}>
            <Box sx={{ display: 'flex' }}>
                <CssBaseline />
                <AppBar position="absolute" open={open}>
                    <Toolbar
                        sx={{
                            pr: '24px', // keep right padding when drawer closed
                        }}
                    >
                        <IconButton
                            edge="start"
                            color="inherit"
                            aria-label="open drawer"
                            onClick={toggleDrawer}
                            sx={{
                                marginRight: '36px',
                                ...(open && { display: 'none' }),
                            }}
                        >
                            <MenuIcon />
                        </IconButton>
                        <Typography
                            component="h1"
                            variant="h6"
                            color="inherit"
                            noWrap
                            sx={{ flexGrow: 1 }}
                        >
                            Résolution pas à pas
                        </Typography>
                    </Toolbar>
                </AppBar>
                <Drawer variant="permanent" open={open}>
                    <Toolbar
                        sx={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'flex-end',
                            px: [1],
                        }}
                    >
                        <IconButton onClick={toggleDrawer}>
                            <ChevronLeftIcon />
                        </IconButton>
                    </Toolbar>
                    <Divider />
                    <List component="nav">
                        {mainListItems}
                        <Divider sx={{ my: 1 }} />
                        {secondaryListItems}
                    </List>
                </Drawer>
                <Box
                    component="main"
                    sx={{
                        backgroundColor: (theme) =>
                            theme.palette.mode === 'light'
                                ? theme.palette.grey[100]
                                : theme.palette.grey[900],
                        flexGrow: 1,
                        height: '100vh',
                        overflow: 'auto',
                    }}
                >
                    <Toolbar />
                    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
                        <Grid container spacing={3}>
                            <Grid item xs={12} md={4}>
                                <Paper
                                    sx={{
                                        p: 2,
                                        display: 'flex',
                                        flexDirection: 'column',
                                    }}
                                >
                                <Typography>Size</Typography>
                                <Slider
                                    value={size}
                                    onChange={(e, newVal) => setSize(newVal)}
                                    aria-labelledby="input-slider"
                                    min={3}
                                    max={10}
                                />
                                <Typography gutterBottom>Selected Size: {size}</Typography> {/* Affiche la valeur de la taille sélectionnée */}

                                <Typography>Number of Symbols</Typography>
                                <Slider
                                    value={symbols}
                                    onChange={(e, newVal) => setSymbols(newVal)}
                                    aria-labelledby="input-slider"
                                    min={1}
                                    max={30}
                                />
                                <Typography gutterBottom>Selected Symbols: {symbols}</Typography> {/* Affiche la valeur des symboles sélectionnés */}
                                    <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                                        <Button onClick={handleStart} variant="contained">Start</Button>
                                        <Button onClick={handleReset} variant="outlined">Reset</Button>
                                    </Box>
                                <Typography>Timer: {timer} seconds</Typography>
                                </Paper>
                            </Grid>
                            <Grid item xs={12} md={8}>
                                <Grid item xs={12} md={8}>
                                    <Paper
                                        sx={{
                                            p: 2,
                                            display: 'flex',
                                            flexDirection: 'column',
                                        }}
                                    >
                                    <Typography variant="h5" gutterBottom component="div">
                                        Shuffled Board
                                    </Typography>
                                    <Box sx={{ marginBottom: 2 }}>
                                        {shuffledBoard.length > 0 ? (
                                            shuffledBoard.map((row, rowIndex) => (
                                                <Box key={rowIndex} sx={{ display: 'flex' }}>
                                                    {row.map((piece, pieceIndex) => (
                                                        <Piece key={`shuffled-${rowIndex}-${pieceIndex}`} piece={piece} />
                                                    ))}
                                                </Box>
                                            ))
                                        ) : (
                                            <Typography>No board to display</Typography>
                                        )}
                                    </Box>

                                    <Typography variant="h5" gutterBottom component="div">
                                        Resolved Board (Step by Step)
                                    </Typography>
                                    <Box>
                                        {resolvedBoard.length > 0 ? (
                                            resolvedBoard.map((row, rowIndex) => (
                                                <Box key={rowIndex} sx={{ display: 'flex' }}>
                                                    {row.map((piece, pieceIndex) => (
                                                        <Piece key={`resolved-${rowIndex}-${pieceIndex}`} piece={piece} />
                                                    ))}
                                                </Box>
                                            ))
                                        ) : (
                                            <Typography>No resolved board to display</Typography>
                                        )}
                                    </Box>
                                    </Paper>
                                </Grid>

                            </Grid>
                        </Grid>
                    </Container>
                </Box>
            </Box>
        </ThemeProvider>
    );
}