import { Box, Card, CardContent, Grid, useTheme, useMediaQuery } from "@mui/material";
import PathManagerGrid from "./PathManagerGrid.tsx";
import { PathManagerTabs } from "./PathManagerTabs.tsx";

function PathManager() {
    const theme = useTheme();
    const isLargeScreen = useMediaQuery(theme.breakpoints.up('lg'));

    return (
        <Box 
            sx={{ 
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                p: 2,
            }}
        >
            <Grid 
                container 
                spacing={3} 
                sx={{ 
                    flex: 1,
                    minHeight: 0,
                    width: '100%',
                    m: 0,
                }}
            >
                {/* Grid Display */}
                <Grid 
                    item 
                    xs={12} 
                    lg={7} 
                    sx={{
                        height: isLargeScreen ? '100%' : 'auto',
                        minHeight: 0,
                        p: '12px !important',
                    }}
                >
                    <Card 
                        elevation={0}
                        sx={{ 
                            height: '100%',
                            display: 'flex',
                            flexDirection: 'column',
                            bgcolor: 'background.paper',
                            border: '1px solid',
                            borderColor: 'divider',
                        }}
                    >
                        <CardContent 
                            sx={{ 
                                flex: 1,
                                p: 3,
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                justifyContent: 'center',
                                minHeight: 0,
                                '&:last-child': { pb: 3 },
                            }}
                        >
                            <Box 
                                sx={{
                                    width: '100%',
                                    height: '100%',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }}
                            >
                                <Box
                                    sx={{
                                        width: 'min(100%, calc(100vh - 250px))',
                                        aspectRatio: '1/1',
                                    }}
                                >
                                    <PathManagerGrid />
                                </Box>
                            </Box>
                        </CardContent>
                    </Card>
                </Grid>

                {/* Controls */}
                <Grid 
                    item 
                    xs={12} 
                    lg={5} 
                    sx={{ 
                        height: isLargeScreen ? '100%' : 'auto',
                        minHeight: 0,
                        p: '12px !important',
                    }}
                >
                    <Card 
                        elevation={0}
                        sx={{ 
                            height: '100%',
                            display: 'flex',
                            flexDirection: 'column',
                            bgcolor: 'background.paper',
                            border: '1px solid',
                            borderColor: 'divider',
                            overflow: 'hidden',
                        }}
                    >
                        <CardContent 
                            sx={{ 
                                p: 3,
                                flex: 1,
                                overflow: 'auto',
                                '&:last-child': { pb: 3 },
                            }}
                        >
                            <PathManagerTabs />
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>
        </Box>
    );
}

export default PathManager;
