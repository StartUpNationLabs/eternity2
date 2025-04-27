import ResponsiveAppBar from "./components/ResponsiveAppBar.tsx";
import { Outlet } from "react-router-dom";
import { Box, Container } from "@mui/material";

export const RootLayout = () => {
    return (
        <Box sx={{ 
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            bgcolor: 'background.default'
        }}>
            <ResponsiveAppBar />
            <Container 
                maxWidth="xl" 
                sx={{ 
                    flex: 1,
                    py: 4,
                    display: 'flex',
                    flexDirection: 'column'
                }}
            >
                <Outlet />
            </Container>
        </Box>
    );
}
