import * as React from "react";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Toolbar from "@mui/material/Toolbar";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import Menu from "@mui/material/Menu";
import MenuIcon from "@mui/icons-material/Menu";
import Container from "@mui/material/Container";
import Button from "@mui/material/Button";
import MenuItem from "@mui/material/MenuItem";
import ExtensionIcon from "@mui/icons-material/Extension";
import { Link, useLocation } from "react-router-dom";

const pages: {
    title: string;
    href: string;
}[] = [
    {
        title: "Do It Yourself",
        href: "/diy",
    },
    {
        title: "Solver",
        href: "/solver",
    },
    {
        title: "Path Creator",
        href: "/path",
    },
];

function ResponsiveAppBar() {
    const [anchorElNav, setAnchorElNav] = React.useState<null | HTMLElement>(null);
    const location = useLocation();

    const handleOpenNavMenu = (event: React.MouseEvent<HTMLElement>) => {
        setAnchorElNav(event.currentTarget);
    };

    const handleCloseNavMenu = () => {
        setAnchorElNav(null);
    };

    return (
        <AppBar 
            position="sticky" 
            elevation={0}
            sx={{
                height: "64px",
                bgcolor: 'background.paper',
                borderBottom: '1px solid',
                borderColor: 'divider',
            }}
        >
            <Container maxWidth="xl">
                <Toolbar disableGutters sx={{ height: '100%' }}>
                    <ExtensionIcon 
                        sx={{ 
                            display: { xs: "none", md: "flex" }, 
                            mr: 1,
                            color: 'primary.main'
                        }}
                    />
                    <Typography
                        variant="h6"
                        noWrap
                        component={Link}
                        to="/"
                        sx={{
                            mr: 4,
                            display: { xs: "none", md: "flex" },
                            fontFamily: "monospace",
                            fontWeight: 700,
                            letterSpacing: ".2rem",
                            color: 'text.primary',
                            textDecoration: "none",
                            '&:hover': {
                                color: 'primary.main',
                            },
                        }}
                    >
                        Eternity II
                    </Typography>

                    <Box sx={{ flexGrow: 1, display: { xs: "flex", md: "none" } }}>
                        <IconButton
                            size="large"
                            aria-label="navigation menu"
                            aria-controls="menu-appbar"
                            aria-haspopup="true"
                            onClick={handleOpenNavMenu}
                            sx={{ color: 'text.primary' }}
                        >
                            <MenuIcon />
                        </IconButton>
                        <Menu
                            id="menu-appbar"
                            anchorEl={anchorElNav}
                            anchorOrigin={{
                                vertical: "bottom",
                                horizontal: "left",
                            }}
                            keepMounted
                            transformOrigin={{
                                vertical: "top",
                                horizontal: "left",
                            }}
                            open={Boolean(anchorElNav)}
                            onClose={handleCloseNavMenu}
                            sx={{
                                display: { xs: "block", md: "none" },
                            }}
                        >
                            {pages.map((page) => (
                                <MenuItem 
                                    key={page.title} 
                                    onClick={handleCloseNavMenu}
                                    component={Link}
                                    to={page.href}
                                    selected={location.pathname === page.href}
                                >
                                    <Typography textAlign="center">{page.title}</Typography>
                                </MenuItem>
                            ))}
                        </Menu>
                    </Box>

                    <ExtensionIcon sx={{ 
                        display: { xs: "flex", md: "none" }, 
                        mr: 1,
                        color: 'primary.main'
                    }}/>
                    <Typography
                        variant="h5"
                        noWrap
                        component={Link}
                        to="/"
                        sx={{
                            mr: 2,
                            display: { xs: "flex", md: "none" },
                            flexGrow: 1,
                            fontFamily: "monospace",
                            fontWeight: 700,
                            letterSpacing: ".2rem",
                            color: 'text.primary',
                            textDecoration: "none",
                            '&:hover': {
                                color: 'primary.main',
                            },
                        }}
                    >
                        Eternity II
                    </Typography>

                    <Box sx={{ flexGrow: 1, display: { xs: "none", md: "flex" } }}>
                        {pages.map((page) => (
                            <Button
                                key={page.title}
                                component={Link}
                                to={page.href}
                                sx={{
                                    mx: 1,
                                    color: location.pathname === page.href ? 'primary.main' : 'text.primary',
                                    fontWeight: location.pathname === page.href ? 600 : 400,
                                    '&:hover': {
                                        bgcolor: 'action.hover',
                                    },
                                }}
                            >
                                {page.title}
                            </Button>
                        ))}
                    </Box>
                </Toolbar>
            </Container>
        </AppBar>
    );
}

export default ResponsiveAppBar;
