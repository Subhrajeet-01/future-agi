import React from "react";
import PropTypes from "prop-types";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Iconify from "src/components/iconify";
import { RouterLink } from "src/routes/components";
import { readableToken } from "../onboarding-home.constants";

const actionHref = (action) => {
  if (!action || action.blocked || !action.routeAvailable || !action.href) {
    return null;
  }
  return action.href;
};

export default function RecommendedActionCard({
  action,
  label,
  variant = "primary",
  onActionClick,
}) {
  const href = actionHref(action);

  if (!action) {
    return (
      <Box
        data-testid={`onboarding-${variant}-action-empty`}
        sx={{
          border: "1px solid",
          borderColor: "divider",
          borderRadius: 1,
          p: 2,
          minHeight: 148,
        }}
      >
        <Typography variant="subtitle2">{label}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>
          No action is available.
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      data-testid={`onboarding-${variant}-action`}
      sx={{
        border: "1px solid",
        borderColor: variant === "primary" ? "primary.main" : "divider",
        borderRadius: 1,
        p: 2,
        minHeight: 188,
        bgcolor: "background.paper",
      }}
    >
      <Stack spacing={1.25}>
        <Stack direction="row" justifyContent="space-between" gap={1}>
          <Typography variant="subtitle2">{label}</Typography>
          <Stack direction="row" spacing={0.75} flexWrap="wrap">
            <Chip
              size="small"
              label={readableToken(action.kind)}
              sx={{ textTransform: "capitalize" }}
            />
            {action.estimatedMinutes ? (
              <Chip
                size="small"
                variant="outlined"
                label={`${action.estimatedMinutes} min`}
              />
            ) : null}
            {action.isSample ? (
              <Chip size="small" variant="outlined" label="Sample" />
            ) : null}
          </Stack>
        </Stack>
        <Stack spacing={0.5}>
          <Typography variant="h6">{action.title}</Typography>
          <Typography variant="body2" color="text.secondary">
            {action.description}
          </Typography>
        </Stack>
        {action.blocked ? (
          <Alert severity="info" sx={{ borderRadius: 1 }}>
            {readableToken(action.blockedReason)}
          </Alert>
        ) : null}
        <Button
          variant={variant === "primary" ? "contained" : "outlined"}
          component={href ? RouterLink : "button"}
          href={href || undefined}
          disabled={!href}
          onClick={() => onActionClick?.(action)}
          startIcon={<Iconify icon="mdi:arrow-right" width={18} />}
          sx={{ alignSelf: "flex-start" }}
        >
          {action.ctaLabel || "Open"}
        </Button>
      </Stack>
    </Box>
  );
}

RecommendedActionCard.propTypes = {
  action: PropTypes.object,
  label: PropTypes.string.isRequired,
  onActionClick: PropTypes.func,
  variant: PropTypes.oneOf(["primary", "fallback"]),
};
