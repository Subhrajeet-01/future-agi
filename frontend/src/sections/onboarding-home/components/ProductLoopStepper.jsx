import React from "react";
import PropTypes from "prop-types";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import {
  ONBOARDING_PRODUCT_LOOP_STEPS,
  readableToken,
} from "../onboarding-home.constants";

export default function ProductLoopStepper({ progress = {} }) {
  return (
    <Box
      data-testid="onboarding-product-loop-stepper"
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 1,
        p: 2,
      }}
    >
      <Stack spacing={1.25}>
        <Typography variant="subtitle2">Product loop</Typography>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              sm: "repeat(2, minmax(0, 1fr))",
              md: "repeat(5, minmax(0, 1fr))",
            },
            gap: 1,
          }}
        >
          {ONBOARDING_PRODUCT_LOOP_STEPS.map((step) => {
            const status = progress[step.id] || "not_started";
            return (
              <Box
                key={step.id}
                sx={{
                  minHeight: 110,
                  border: "1px solid",
                  borderColor:
                    status === "complete" ? "success.main" : "divider",
                  borderRadius: 1,
                  p: 1.25,
                  bgcolor: status === "selected" ? "action.hover" : "inherit",
                }}
              >
                <Stack spacing={0.75}>
                  <Stack direction="row" alignItems="center" spacing={0.75}>
                    <Typography variant="subtitle2">{step.label}</Typography>
                    <Chip
                      size="small"
                      label={readableToken(status)}
                      color={status === "complete" ? "success" : "default"}
                      variant={status === "complete" ? "filled" : "outlined"}
                      sx={{ textTransform: "capitalize" }}
                    />
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    {step.description}
                  </Typography>
                </Stack>
              </Box>
            );
          })}
        </Box>
      </Stack>
    </Box>
  );
}

ProductLoopStepper.propTypes = {
  progress: PropTypes.object,
};
