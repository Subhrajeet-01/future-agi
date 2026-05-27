import React, { useMemo } from "react";
import PropTypes from "prop-types";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useLocation } from "react-router-dom";
import { useAuthContext } from "src/auth/hooks";
import Iconify from "src/components/iconify";
import { useWorkspace } from "src/contexts/WorkspaceContext";
import { RouterLink } from "src/routes/components";
import { useActivationState } from "./hooks/useActivationState";
import OnboardingHomeError from "./components/OnboardingHomeError";
import OnboardingHomeSkeleton from "./components/OnboardingHomeSkeleton";

const STAGE_COPY = {
  feature_disabled: {
    eyebrow: "Setup",
    title: "Start with the setup checklist",
    description: "The existing checklist is available for this workspace.",
  },
  workspace_missing: {
    eyebrow: "Workspace",
    title: "Choose a workspace",
    description: "Select a workspace before starting a product loop.",
  },
  permission_limited: {
    eyebrow: "Access",
    title: "Request access for setup",
    description: "This workspace needs write access before setup can continue.",
  },
  choose_goal: {
    eyebrow: "First goal",
    title: "Choose what to set up first",
    description: "Pick the first product job before moving into setup.",
  },
  selected_path_unavailable: {
    eyebrow: "Path unavailable",
    title: "Start with an available path",
    description: "This selected path is not available in the product yet.",
  },
  connect_observability: {
    eyebrow: "Observe",
    title: "Connect observability",
    description: "Create an observe project and send one trace.",
  },
  waiting_for_first_trace: {
    eyebrow: "Waiting",
    title: "Waiting for the first trace",
    description: "Once a trace lands, the next review action will unlock.",
  },
  waiting_for_first_trace_sample_available: {
    eyebrow: "Waiting",
    title: "Waiting for real data",
    description: "Use a sample signal while the first real trace is pending.",
  },
  review_first_trace: {
    eyebrow: "First signal",
    title: "Review the first trace",
    description:
      "Inspect the first trace and capture the first quality signal.",
  },
  create_trace_evaluator: {
    eyebrow: "Quality loop",
    title: "Create an evaluator",
    description: "Turn the reviewed trace into a repeatable quality check.",
  },
  activated: {
    eyebrow: "Activated",
    title: "First quality loop is ready",
    description: "The workspace has completed a first meaningful loop.",
  },
  daily_review: {
    eyebrow: "Daily quality",
    title: "Review today's quality signal",
    description: "Open the latest quality signal and keep the loop fresh.",
  },
  review_sample_signal: {
    eyebrow: "Sample data",
    title: "Review a sample signal",
    description:
      "Inspect the sample signal while real workspace data is pending.",
  },
};

const getStageCopy = (state) =>
  STAGE_COPY[state?.stage] || {
    eyebrow: "Setup",
    title: "Open Get Started",
    description: "The existing setup checklist is available.",
  };

const readableToken = (value) =>
  value ? String(value).replaceAll("_", " ") : "not set";

const actionHref = (action) => {
  if (!action || action.blocked || !action.routeAvailable || !action.href) {
    return null;
  }
  return action.href;
};

function ActionSlot({ action, label, variant = "primary" }) {
  const href = actionHref(action);
  if (!action) {
    return (
      <Box
        sx={{
          border: "1px solid",
          borderColor: "divider",
          borderRadius: 1,
          p: 2,
          minHeight: 136,
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
        minHeight: 172,
        bgcolor: "background.paper",
      }}
    >
      <Stack spacing={1.25}>
        <Stack direction="row" justifyContent="space-between" gap={1}>
          <Typography variant="subtitle2">{label}</Typography>
          <Chip
            size="small"
            label={readableToken(action.kind)}
            sx={{ textTransform: "capitalize" }}
          />
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
          startIcon={<Iconify icon="mdi:arrow-right" width={18} />}
          sx={{ alignSelf: "flex-start" }}
        >
          {action.ctaLabel || "Open"}
        </Button>
      </Stack>
    </Box>
  );
}

ActionSlot.propTypes = {
  action: PropTypes.object,
  label: PropTypes.string.isRequired,
  variant: PropTypes.oneOf(["primary", "fallback"]),
};

function PathRows({ paths: availablePaths = [] }) {
  if (!availablePaths.length) return null;

  return (
    <Box
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
          {availablePaths.map((path) => (
            <Box
              key={path.id}
              sx={{
                minHeight: 86,
                border: "1px solid",
                borderColor: path.isAvailable ? "divider" : "action.disabled",
                borderRadius: 1,
                p: 1.5,
                bgcolor:
                  path.status === "selected" ? "action.hover" : "inherit",
              }}
            >
              <Stack spacing={0.5}>
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
              </Stack>
            </Box>
          ))}
        </Box>
      </Stack>
    </Box>
  );
}

PathRows.propTypes = {
  paths: PropTypes.array,
};

function Diagnostics({ state }) {
  if (!state?.featureFlags?.onboarding_debug || !state?.diagnostics) {
    return null;
  }

  return (
    <Box
      data-testid="onboarding-diagnostics"
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 1,
        p: 2,
      }}
    >
      <Typography variant="subtitle2">Diagnostics</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
        {state.diagnostics.decisionReason || "No decision reason returned."}
      </Typography>
    </Box>
  );
}

Diagnostics.propTypes = {
  state: PropTypes.object,
};

export default function OnboardingHomeView() {
  const { user } = useAuthContext();
  const {
    currentWorkspaceId,
    currentWorkspaceDisplayName,
    isReady: workspaceReady,
  } = useWorkspace();
  const location = useLocation();

  const searchContext = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return {
      source: params.get("source") || "home",
      campaignKey: params.get("campaign_key"),
      emailKey: params.get("email_key"),
      targetStage: params.get("target_stage"),
      targetEvent: params.get("target_event"),
      targetRoute: params.get("target_route"),
      linkIssuedAt: params.get("link_issued_at"),
      mode: params.get("mode"),
    };
  }, [location.search]);

  const workspaceId = currentWorkspaceId || user?.default_workspace_id || null;
  const organizationId =
    user?.organization?.id || user?.organization_id || null;
  const waitingForWorkspace =
    Boolean(user?.default_workspace_id) && !workspaceId && !workspaceReady;

  const { state, isLoading, isError, error, refetch } = useActivationState({
    organizationId,
    workspaceId,
    ...searchContext,
    enabled: Boolean(user) && !waitingForWorkspace,
    requireWorkspaceContext: false,
  });

  if (isLoading || waitingForWorkspace || (!state && !isError)) {
    return <OnboardingHomeSkeleton />;
  }

  if (isError) {
    return <OnboardingHomeError error={error} onRetry={refetch} />;
  }

  const copy = getStageCopy(state);
  const fallbackAction = state.fallbackAction;

  return (
    <Box
      data-testid="onboarding-home-view"
      sx={{
        width: "100%",
        minHeight: "calc(100vh - 120px)",
        bgcolor: "background.paper",
        p: { xs: 2, md: 3 },
      }}
    >
      <Stack spacing={3} sx={{ maxWidth: 1180, mx: "auto" }}>
        <Stack spacing={1}>
          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
            flexWrap="wrap"
          >
            <Chip size="small" label={copy.eyebrow} />
            {state.isActivated ? (
              <Chip size="small" color="success" label="Activated" />
            ) : null}
          </Stack>
          <Typography variant="h3">{copy.title}</Typography>
          <Typography variant="body1" color="text.secondary" maxWidth={760}>
            {copy.description}
          </Typography>
          {currentWorkspaceDisplayName ? (
            <Typography variant="body2" color="text.secondary">
              Workspace: {currentWorkspaceDisplayName}
            </Typography>
          ) : null}
        </Stack>

        {state.stage === "feature_disabled" ? (
          <Alert severity="info" sx={{ borderRadius: 1 }}>
            The existing setup checklist is available for this workspace.
          </Alert>
        ) : null}

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "minmax(0, 2fr) 1fr" },
            gap: 2,
            alignItems: "stretch",
          }}
        >
          <ActionSlot
            action={state.recommendedAction}
            label="Recommended action"
          />
          <ActionSlot
            action={fallbackAction}
            label="Fallback"
            variant="fallback"
          />
        </Box>

        <Box
          sx={{
            border: "1px solid",
            borderColor: "divider",
            borderRadius: 1,
            p: 2,
          }}
        >
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle2">Current stage</Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mt: 0.5, textTransform: "capitalize" }}
              >
                {readableToken(state.stage)}
              </Typography>
            </Box>
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle2">Selected path</Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mt: 0.5, textTransform: "capitalize" }}
              >
                {readableToken(state.primaryPath)}
              </Typography>
            </Box>
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle2">Goal</Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mt: 0.5, textTransform: "capitalize" }}
              >
                {readableToken(state.goal)}
              </Typography>
            </Box>
          </Stack>
        </Box>

        <PathRows paths={state.availablePaths} />
        <Diagnostics state={state} />
      </Stack>
    </Box>
  );
}
