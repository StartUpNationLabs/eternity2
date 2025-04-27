import { SolverSolveResponse } from "../../proto/solver/v1/solver.ts";
import { Box, Card, CardContent, Grid, Typography, useTheme } from "@mui/material";
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import SpeedIcon from '@mui/icons-material/Speed';
import MemoryIcon from '@mui/icons-material/Memory';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  subtitle?: string;
}

const StatCard = ({ title, value, icon, subtitle }: StatCardProps) => {
  const theme = useTheme();
  
  return (
    <Card 
      elevation={0}
      sx={{ 
        height: '100%',
        bgcolor: 'background.paper',
        border: '1px solid',
        borderColor: 'divider',
        transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: theme.shadows[4],
        }
      }}
    >
      <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
          <Box sx={{ color: 'primary.main', mr: 1, display: 'flex', '& > svg': { fontSize: '1.2rem' } }}>
            {icon}
          </Box>
          <Typography 
            variant="body2" 
            color="text.secondary"
            sx={{ fontWeight: 500 }}
          >
            {title}
          </Typography>
        </Box>
        <Typography 
          variant="h5" 
          component="div"
          sx={{ 
            fontWeight: 600,
            color: 'text.primary',
            mb: subtitle ? 0.25 : 0,
            fontSize: '1.5rem'
          }}
        >
          {typeof value === 'number' ? value.toLocaleString() : value}
        </Typography>
        {subtitle && (
          <Typography 
            variant="caption" 
            color="text.secondary"
            sx={{ 
              display: 'block',
              fontSize: '0.75rem'
            }}
          >
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export const Stats = (props: { response?: SolverSolveResponse }) => {
  if (!props.response) {
    return (
      <Box sx={{ p: 1.5 }}>
        <Typography 
          variant="subtitle1" 
          sx={{ 
            mb: 1.5,
            fontWeight: 600,
            color: 'text.primary'
          }}
        >
          Solver Statistics
        </Typography>
        <Card elevation={0}>
          <CardContent sx={{ py: 1, px: 1.5 }}>
            <Typography color="text.secondary" variant="body2">
              No statistics available yet
            </Typography>
          </CardContent>
        </Card>
      </Box>
    );
  }

  const {
    time,
    hashesPerSecond,
    hashTableSize,
    boardsPerSecond,
    boardsAnalyzed,
    hashTableHits
  } = props.response;

  return (
    <Box sx={{ p: 1.5 }}>
      <Typography 
        variant="subtitle1" 
        sx={{ 
          mb: 1.5,
          fontWeight: 600,
          color: 'text.primary'
        }}
      >
        Solver Statistics
      </Typography>
      
      <Grid container spacing={1.5} direction="column">
        <Grid item xs={12}>
          <StatCard
            title="Time Elapsed"
            value={time.toFixed(3)}
            icon={<AccessTimeIcon />}
            subtitle="seconds"
          />
        </Grid>
        <Grid item xs={12}>
          <StatCard
            title="Processing Speed"
            value={boardsPerSecond.toFixed(0)}
            icon={<SpeedIcon />}
            subtitle="boards per second"
          />
        </Grid>
        <Grid item xs={12}>
          <StatCard
            title="Hash Performance"
            value={hashesPerSecond.toFixed(1)}
            icon={<MemoryIcon />}
            subtitle={`${hashTableSize.toLocaleString()} total hashes`}
          />
        </Grid>
        <Grid item xs={12}>
          <StatCard
            title="Boards Analyzed"
            value={boardsAnalyzed}
            icon={<CheckCircleOutlineIcon />}
            subtitle={`${hashTableHits.toLocaleString()} cache hits`}
          />
        </Grid>
      </Grid>
    </Box>
  );
};