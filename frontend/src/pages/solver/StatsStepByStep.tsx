import { SolverStepByStepResponse } from "../../proto/solver/v1/solver.ts";
import { Box, Card, CardContent, Grid, Typography, useTheme } from "@mui/material";
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import SpeedIcon from '@mui/icons-material/Speed';
import ExtensionIcon from '@mui/icons-material/Extension';
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
      <CardContent sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <Box sx={{ color: 'primary.main', mr: 1 }}>
            {icon}
          </Box>
          <Typography 
            variant="subtitle2" 
            color="text.secondary"
            sx={{ fontWeight: 500 }}
          >
            {title}
          </Typography>
        </Box>
        <Typography 
          variant="h4" 
          component="div"
          sx={{ 
            fontWeight: 600,
            color: 'text.primary',
            mb: subtitle ? 0.5 : 0
          }}
        >
          {typeof value === 'number' ? value.toLocaleString() : value}
        </Typography>
        {subtitle && (
          <Typography 
            variant="caption" 
            color="text.secondary"
            sx={{ display: 'block' }}
          >
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export const StatsStepByStep = (props: { response?: SolverStepByStepResponse }) => {
  if (!props.response) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography 
          variant="h6" 
          sx={{ 
            mb: 2,
            fontWeight: 600,
            color: 'text.primary'
          }}
        >
          Step-by-Step Statistics
        </Typography>
        <Card elevation={0}>
          <CardContent>
            <Typography color="text.secondary">
              No statistics available yet
            </Typography>
          </CardContent>
        </Card>
      </Box>
    );
  }

  const {
    time,
    boardsPerSecond,
    boardsAnalyzed,
    steps
  } = props.response;

  return (
    <Box sx={{ p: 2 }}>
      <Typography 
        variant="h6" 
        sx={{ 
          mb: 2,
          fontWeight: 600,
          color: 'text.primary'
        }}
      >
        Step-by-Step Statistics
      </Typography>
      
      <Grid container spacing={2}>
        <Grid item xs={12} sm={6}>
          <StatCard
            title="Time Elapsed"
            value={time.toFixed(3)}
            icon={<AccessTimeIcon />}
            subtitle="seconds"
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <StatCard
            title="Processing Speed"
            value={boardsPerSecond.toFixed(0)}
            icon={<SpeedIcon />}
            subtitle="boards per second"
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <StatCard
            title="Pieces Placed"
            value={steps}
            icon={<ExtensionIcon />}
            subtitle="current progress"
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <StatCard
            title="Boards Analyzed"
            value={boardsAnalyzed}
            icon={<CheckCircleOutlineIcon />}
            subtitle="total configurations checked"
          />
        </Grid>
      </Grid>
    </Box>
  );
};