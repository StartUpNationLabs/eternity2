import { Box, Container, Typography, Grid, Card, CardContent, useTheme } from "@mui/material";
import { RotatedPiece } from "../../proto/solver/v1/solver.ts";
import { Link } from "react-router-dom";
import { useState, useEffect } from "react";
import Board from "../../components/Board.tsx";
import { createBoard, convertToPieces } from "../../utils/logic.tsx";
import { BOARD_COLOR_DEFAULT } from "../../utils/Constants.tsx";
import ConstructionIcon from "@mui/icons-material/Construction";
import CalculateIcon from "@mui/icons-material/Calculate";
import RouteIcon from "@mui/icons-material/Route";

function HomePage() {
  const theme = useTheme();
  const [puzzlePieces, setPuzzlePieces] = useState<RotatedPiece[]>([]);

  // Generate a non-shuffled 16x16 puzzle on component mount
  useEffect(() => {
    // Create a standard board without shuffling
    const boardSize = 16;
    const board = createBoard(boardSize, BOARD_COLOR_DEFAULT);
    const pieces = convertToPieces(board);
    
    // Convert to RotatedPieces without rotation
    const rotatedPieces = pieces.map((piece, index) => ({
      piece: piece,
      rotation: 0, // No rotation
      index: index
    }));
    
    setPuzzlePieces(rotatedPieces);
  }, []);

  return (
    <Box sx={{ 
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* Hero Section - Compact design */}
      <Container 
        maxWidth="lg" 
        sx={{ 
          pt: { xs: 2, md: 2 }, 
          pb: { xs: 1, md: 1 },
          display: 'flex',
          flexDirection: 'column',
          flex: '0 0 auto'
        }}
      >
        <Box sx={{ 
          display: 'flex', 
          flexDirection: { xs: 'column', md: 'row' },
          alignItems: 'center',
          gap: { xs: 2, md: 4 }
        }}>
          <Box sx={{ 
            flex: 1,
            order: { xs: 2, md: 1 }
          }}>
            <Typography 
              variant="h2" 
              component="h1"
              sx={{ 
                fontWeight: 700,
                mb: 1,
                fontSize: { xs: '2rem', md: '3rem' }
              }}
            >
              Eternity II
            </Typography>
            
            <Typography 
              variant="h6" 
              component="p"
              color="text.secondary"
              sx={{ mb: 1.5 }}
            >
              Explore one of the world's most challenging puzzles
            </Typography>
            
            <Typography 
              variant="body2" 
              paragraph
              sx={{ mb: 1 }}
            >
              The Eternity II puzzle is a famous edge-matching puzzle released in 2007 with a $2 million prize for the first complete solution. With 256 unique pieces and over 10<sup>500</sup> possible arrangements, it remains one of the hardest combinatorial optimization problems.
            </Typography>
            
            <Typography 
              variant="body2"
            >
              This platform offers you three ways to engage with the puzzle: try it yourself, explore solution paths, or use our powerful solver algorithms.
            </Typography>
          </Box>
          
          {/* Show puzzle on all screen sizes, including phones */}
          <Box sx={{ 
            flex: { xs: 'none', sm: 1, md: 0.8 }, 
            display: 'flex', 
            justifyContent: 'center',
            alignItems: 'center',
            width: { xs: '100%', sm: 'auto' },
            order: { xs: 1, md: 2 },
            mb: { xs: 1, sm: 0 }
          }}>
            {/* Puzzle display with improved styling and responsive sizing */}
            <Box sx={{ 
              width: { xs: '200px', sm: '240px', md: '280px' },
              height: { xs: '200px', sm: '240px', md: '280px' },
              boxShadow: 3,
              borderRadius: 2,
              p: 1,
              bgcolor: 'background.paper',
              overflow: 'hidden'
            }}>
              {puzzlePieces.length > 0 && (
                <Board pieces={puzzlePieces} />
              )}
            </Box>
          </Box>
        </Box>
      </Container>
      
      {/* Divider */}
      <Box sx={{ 
        width: '100%', 
        height: '1px', 
        bgcolor: 'divider', 
        mb: 2, 
        mt: 2 
      }} />
      
      {/* Features Section - More compact */}
      <Container 
        maxWidth="lg" 
        sx={{ 
          flex: 1, 
          display: 'flex', 
          flexDirection: 'column',
          minHeight: 0
        }}
      >
        <Typography 
          variant="h4" 
          component="h2"
          align="center"
          sx={{ 
            mb: 2,
            fontWeight: 600,
            fontSize: { xs: '1.5rem', md: '2rem' }
          }}
        >
          Our Features
        </Typography>
        
        <Grid container spacing={2} sx={{ flex: 1, minHeight: 0 }}>
          {/* Do It Yourself */}
          <Grid item xs={12} md={4}>
            <Card 
              component={Link}
              to="/diy"
              elevation={0}
              sx={{ 
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                bgcolor: 'background.paper',
                border: '1px solid',
                borderColor: 'divider',
                transition: 'all 0.2s ease',
                textDecoration: 'none',
                color: 'inherit',
                borderRadius: 2,
                '&:hover': {
                  borderColor: 'primary.main',
                  transform: 'translateY(-3px)',
                  boxShadow: theme.shadows[3]
                }
              }}
            >
              <CardContent sx={{ p: 2, flex: 1 }}>
                <Box sx={{ 
                  display: 'flex', 
                  justifyContent: 'center', 
                  mb: 1.5 
                }}>
                  <ConstructionIcon sx={{ fontSize: 45, color: 'primary.main' }} />
                </Box>
                <Typography 
                  variant="h6" 
                  component="h3" 
                  gutterBottom
                  align="center"
                  sx={{ fontWeight: 600, mb: 1 }}
                >
                  Do It Yourself
                </Typography>
                <Typography variant="body2">
                  Try to solve Eternity II puzzles on your own. Drag, drop, and rotate pieces to find the perfect arrangement. Challenge yourself with various grid sizes.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          {/* Solver */}
          <Grid item xs={12} md={4}>
            <Card 
              component={Link}
              to="/solver"
              elevation={0}
              sx={{ 
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                bgcolor: 'background.paper',
                border: '1px solid',
                borderColor: 'divider',
                transition: 'all 0.2s ease',
                textDecoration: 'none',
                color: 'inherit',
                borderRadius: 2,
                '&:hover': {
                  borderColor: 'primary.main',
                  transform: 'translateY(-3px)',
                  boxShadow: theme.shadows[3]
                }
              }}
            >
              <CardContent sx={{ p: 2, flex: 1 }}>
                <Box sx={{ 
                  display: 'flex', 
                  justifyContent: 'center', 
                  mb: 1.5 
                }}>
                  <CalculateIcon sx={{ fontSize: 45, color: 'primary.main' }} />
                </Box>
                <Typography 
                  variant="h6" 
                  component="h3" 
                  gutterBottom
                  align="center"
                  sx={{ fontWeight: 600, mb: 1 }}
                >
                  Solver
                </Typography>
                <Typography variant="body2">
                  Witness our algorithms work through the puzzle step by step. Customize the board generation, set constraints, and watch our solver in action.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          {/* Path Creator */}
          <Grid item xs={12} md={4}>
            <Card 
              component={Link}
              to="/path"
              elevation={0}
              sx={{ 
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                bgcolor: 'background.paper',
                border: '1px solid',
                borderColor: 'divider',
                transition: 'all 0.2s ease',
                textDecoration: 'none',
                color: 'inherit',
                borderRadius: 2,
                '&:hover': {
                  borderColor: 'primary.main',
                  transform: 'translateY(-3px)',
                  boxShadow: theme.shadows[3]
                }
              }}
            >
              <CardContent sx={{ p: 2, flex: 1 }}>
                <Box sx={{ 
                  display: 'flex', 
                  justifyContent: 'center', 
                  mb: 1.5 
                }}>
                  <RouteIcon sx={{ fontSize: 45, color: 'primary.main' }} />
                </Box>
                <Typography 
                  variant="h6" 
                  component="h3" 
                  gutterBottom
                  align="center"
                  sx={{ fontWeight: 600, mb: 1 }}
                >
                  Path Creator
                </Typography>
                <Typography variant="body2">
                  Explore different solution paths and strategies. Visualize the solving process, analyze approaches, and understand the complexities behind Eternity II.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
}

export default HomePage; 