import React from "react";
import PropTypes from "prop-types";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { ObservePanelActions, ObservePanelHeader } from "./observe-panel-utils";

export default function FirstLoopCompletePanel({
  action,
  fallbackAction,
  lastMeaningfulEvent,
  onPrimaryClick,
  onFallbackClick,
  onCheckAgain,
  isChecking = false,
}) {
  return (
    <Box
      data-testid="first-loop-complete-panel"
      sx={{
        border: "1px solid",
        borderColor: "success.main",
        borderRadius: 1,
        p: 2,
        bgcolor: "background.paper",
      }}
    >
      <Stack spacing={2}>
        <ObservePanelHeader
          eyebrow="First loop complete"
          title="The first quality loop is ready"
          description="Keep reviewing the observe signal and turn future regressions into quality checks."
          chips={["observe", "complete"]}
        />
        {lastMeaningfulEvent ? (
          <Box
            sx={{
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 1,
              p: 1.5,
            }}
          >
            <Typography variant="subtitle2">Latest proof</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {lastMeaningfulEvent.name}
            </Typography>
          </Box>
        ) : null}
        <ObservePanelActions
          action={action}
          fallbackAction={fallbackAction}
          onPrimaryClick={onPrimaryClick}
          onFallbackClick={onFallbackClick}
          onCheckAgain={onCheckAgain}
          isChecking={isChecking}
        />
      </Stack>
    </Box>
  );
}

FirstLoopCompletePanel.propTypes = {
  action: PropTypes.object,
  fallbackAction: PropTypes.object,
  isChecking: PropTypes.bool,
  lastMeaningfulEvent: PropTypes.object,
  onCheckAgain: PropTypes.func,
  onFallbackClick: PropTypes.func,
  onPrimaryClick: PropTypes.func,
};
