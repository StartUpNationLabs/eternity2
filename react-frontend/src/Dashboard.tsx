import React, { useState, useEffect } from 'react';
import { styled, ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box, Container, Grid, Slider, Button, Typography, AppBar, Toolbar, IconButton } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import Piece from './Piece';
import {createBoard, PieceData, rotatePiece, shuffleAndRotateBoard} from "./logic.tsx";
import {GrpcWebFetchTransport} from "@protobuf-ts/grpcweb-transport";
import {SolverClient} from "./proto/solver/v1/solver.client.ts";

const drawerWidth = 240;

const Main = styled('main', { shouldForwardProp: prop => prop !== 'open' })(({ theme, open }) => ({
    flexGrow: 1,
    padding: theme.spacing(3),
    transition: theme.transitions.create('margin', {
        easing: theme.transitions.easing.sharp,
        duration: theme.transitions.duration.leavingScreen,
    }),
    marginLeft: `-${drawerWidth}px`,
    ...(open && {
        transition: theme.transitions.create('margin', {
            easing: theme.transitions.easing.easeOut,
            duration: theme.transitions.duration.enteringScreen,
        }),
        marginLeft: 0,
    }),
}));

const AppBarDrawer = styled(AppBar, { shouldForwardProp: prop => prop !== 'open' })(({ theme, open }) => ({
    transition: theme.transitions.create(['margin', 'width'], {
        easing: theme.transitions.easing.sharp,
        duration: theme.transitions.duration.leavingScreen,
    }),
    ...(open && {
        width: `calc(100% - ${drawerWidth}px)`,
        marginLeft: `${drawerWidth}px`,
        transition: theme.transitions.create(['margin', 'width'], {
            easing: theme.transitions.easing.easeOut,
            duration: theme.transitions.duration.enteringScreen,
        }),
    }),
}));

const DrawerHeader = styled('div')(({ theme }) => ({
    display: 'flex',
    alignItems: 'center',
    padding: theme.spacing(0, 1),
    ...theme.mixins.toolbar,
    justifyContent: 'flex-end',
}));

const defaultTheme = createTheme();

export default function Dashboard() {
    const [open, setOpen] = useState(false);
    const [size, setSize] = useState(5);
    const [symbols, setSymbols] = useState(5);
    const [timer, setTimer] = useState(0);
    const [timerActive, setTimerActive] = useState(false);
    const [board, setBoard] = useState<PieceData[][]>([]);
    const [shuffledBoard, setShuffledBoard] = useState<PieceData[][]>([]);
    const [resolvedBoard, setResolvedBoard] = useState<PieceData[][]>([]); // New state for the resolved board
    const [shouldResolve, setShouldResolve] = useState(false); // Nouvel état pour contrôler le lancement de la résolution


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

    const handleDrawerOpen = () => {
        setOpen(true);
    };
    const resolveAndDisplayBoard = async () => {
        setTimerActive(true);
        const transport = new GrpcWebFetchTransport({
            baseUrl: "http://vmpx15.polytech.hs.ozeliurs.com:50052",
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

    const handleDrawerClose = () => {
        setOpen(false);
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

    return (
        <ThemeProvider theme={defaultTheme}>
            <Box sx={{ display: 'flex' }}>
                <CssBaseline />
                <AppBarDrawer position="fixed" open={open}>
                    <Toolbar>
                        <IconButton color="inherit" aria-label="open drawer" onClick={handleDrawerOpen} edge="start" sx={{ mr: 2, ...(open && { display: 'none' }) }}>
                            <MenuIcon />
                        </IconButton>
                        <Typography variant="h6" noWrap component="div">
                            Puzzle Solver
                        </Typography>
                    </Toolbar>
                </AppBarDrawer>
                <Main open={open}>
                    <DrawerHeader>
                        <IconButton onClick={handleDrawerClose}>
                            <ChevronLeftIcon />
                        </IconButton>
                    </DrawerHeader>
                    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
                        <Grid container spacing={3}>
                            <Grid item xs={12} md={4}>
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

                                <Button onClick={handleStart} variant="contained">Start</Button>
                                <Button onClick={handleReset} variant="outlined">Reset</Button>
                                <Typography>Timer: {timer} seconds</Typography>
                            </Grid>
                            <Grid item xs={12} md={8}>
                                <Grid item xs={12} md={8}>
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
                                </Grid>

                            </Grid>
                        </Grid>
                    </Container>
                </Main>
            </Box>
        </ThemeProvider>
    );
}
