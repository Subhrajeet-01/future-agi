import React from "react";
import PropTypes from "prop-types";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Iconify from "src/components/iconify";
import { RouterLink } from "src/routes/components";
import { readableToken } from "../onboarding-home.constants";

const pathButtonLabel = (path) => {
  if (path.status === "selected") return "Current";
  if (!path.isAvailable) return "Unavailable";
  return "Focus";
};

export default function PathCardGrid({
  isChangingPath = false,
  paths = [],
  onPathClick,
}) {
  if (!paths.length) return null;

  return (
    <Box
      data-testid="onboarding-path-card-grid"
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 1,
        p: 2,
      }}
    >
      <Stack spacing={1.25}>
        <Typography variant="subtitle2">Available paths</Typography>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" },
            gap: 1,
          }}
        >
          {paths.map((path) => {
            const isSelected = path.status === "selected";
            const isDisabled =
              !path.isAvailable || isSelected || isChangingPath;
            const href =
              !onPathClick && path.isAvailable && path.href ? path.href : null;
            return (
              <Box
                key={path.id}
                data-testid={`onboarding-path-card-${path.id}`}
                sx={{
                  minHeight: 132,
                  border: "1px solid",
                  borderColor: path.isAvailable ? "divider" : "action.disabled",
                  borderRadius: 1,
                  p: 1.5,
                  bgcolor:
                    path.status === "selected" ? "action.hover" : "inherit",
                  opacity: path.isAvailable ? 1 : 0.64,
                }}
              >
                <Stack spacing={1} sx={{ height: "100%" }}>
                  <Stack direction="row" alignItems="center" spacing={1}>
                    <Typography variant="subtitle2">{path.label}</Typography>
                    <Chip
                      size="small"
                      label={readableToken(path.status)}
                      sx={{ textTransform: "capitalize" }}
                    />
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    {path.description}
                  </Typography>
                  {path.blockedReason ? (
                    <Typography variant="caption" color="text.secondary">
                      {readableToken(path.blockedReason)}
                    </Typography>
                  ) : null}
                  <Box sx={{ flexGrow: 1 }} />
                  <Button
                    size="small"
                    variant="text"
                    component={href ? RouterLink : "button"}
                    href={href || undefined}
                    disabled={isDisabled}
                    onClick={() => onPathClick?.(path)}
                    endIcon={<Iconify icon="mdi:arrow-right" width={16} />}
                    sx={{ alignSelf: "flex-start", px: 0.5 }}
                  >
                    {pathButtonLabel(path)}
                  </Button>
                </Stack>
              </Box>
            );
          })}
        </Box>
      </Stack>
    </Box>
  );
}

PathCardGrid.propTypes = {
  isChangingPath: PropTypes.bool,
  onPathClick: PropTypes.func,
  paths: PropTypes.array,
};
