import React from "react";
import PropTypes from "prop-types";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Iconify from "src/components/iconify";
import { RouterLink } from "src/routes/components";
import { paths } from "src/routes/paths";

export default function OnboardingHomeError({ error, onRetry }) {
  const message =
    error?.result?.message ||
    error?.message ||
    "Home could not load right now.";

  return (
    <Box
      data-testid="onboarding-home-error"
      sx={{
        width: "100%",
        minHeight: "calc(100vh - 120px)",
        bgcolor: "background.paper",
        p: { xs: 2, md: 3 },
      }}
    >
      <Stack spacing={2} sx={{ maxWidth: 720, mx: "auto" }}>
        <Alert severity="warning" sx={{ borderRadius: 1 }}>
          {message}
        </Alert>
        <Stack spacing={0.75}>
          <Typography variant="h4">Open Get Started instead</Typography>
          <Typography variant="body2" color="text.secondary">
            The existing setup checklist is still available.
          </Typography>
        </Stack>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25}>
          <Button
            variant="contained"
            onClick={onRetry}
            startIcon={<Iconify icon="mdi:refresh" width={18} />}
          >
            Retry
          </Button>
          <Button
            variant="outlined"
            component={RouterLink}
            href={paths.dashboard.getstarted}
            startIcon={<Iconify icon="mdi:arrow-right" width={18} />}
          >
            Get Started
          </Button>
        </Stack>
      </Stack>
    </Box>
  );
}

OnboardingHomeError.propTypes = {
  error: PropTypes.object,
  onRetry: PropTypes.func,
};
