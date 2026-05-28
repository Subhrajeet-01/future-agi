const DEFAULT_ARTIFACT_ID = "observe-onboarding";

export const OBSERVE_ONBOARDING_MODES = {
  CREATE_EVALUATOR: "create-evaluator",
  SEND_FIRST_TRACE: "send-first-trace",
};

const modeSet = new Set(Object.values(OBSERVE_ONBOARDING_MODES));

const safeKeyPart = (value, fallback = DEFAULT_ARTIFACT_ID) =>
  String(value || fallback)
    .replace(/[^A-Za-z0-9_.:-]/g, "-")
    .slice(0, 64);

const compactMetadata = (value = {}) =>
  Object.fromEntries(
    Object.entries(value).filter(
      ([, item]) => item !== undefined && item !== null && item !== "",
    ),
  );

export const getObserveOnboardingParams = (search = "") => {
  const params = new URLSearchParams(search);
  const isOnboarding = params.get("source") === "onboarding";
  const rawMode = params.get("onboarding");
  return {
    isOnboarding,
    mode: isOnboarding && modeSet.has(rawMode) ? rawMode : null,
  };
};

export const observeOnboardingStage = (mode) => {
  if (mode === OBSERVE_ONBOARDING_MODES.CREATE_EVALUATOR) {
    return "create_trace_evaluator";
  }
  return "waiting_for_first_trace";
};

export const getObserveOnboardingCopy = (mode) => {
  if (mode === OBSERVE_ONBOARDING_MODES.SEND_FIRST_TRACE) {
    return {
      currentStep: "First trace",
      description:
        "Send one production or test trace to unlock the first review step.",
      primaryLabel: "Refresh traces",
      secondaryLabel: "Open setup",
      steps: [
        { label: "Project", complete: true },
        { label: "Trace", complete: false },
        { label: "Review", complete: false },
      ],
      title: "Send the first trace",
    };
  }

  if (mode === OBSERVE_ONBOARDING_MODES.CREATE_EVALUATOR) {
    return {
      currentStep: "Evaluator",
      description:
        "Turn the reviewed trace into a repeatable quality check for future runs.",
      primaryLabel: "Create evaluator",
      secondaryLabel: "Refresh traces",
      steps: [
        { label: "Project", complete: true },
        { label: "Trace review", complete: true },
        { label: "Evaluator", complete: false },
      ],
      title: "Create an evaluator",
    };
  }

  return null;
};

export const buildObserveProjectOnboardingHref = ({ observeId, mode } = {}) => {
  if (!observeId) return "/dashboard/observe";
  const params = new URLSearchParams();
  params.set("source", "onboarding");
  if (modeSet.has(mode)) params.set("onboarding", mode);
  return `/dashboard/observe/${observeId}/llm-tracing?${params.toString()}`;
};

export const buildObserveEvaluatorCreateHref = ({ observeId } = {}) => {
  const params = new URLSearchParams();
  params.set("source", "onboarding");
  params.set("step", "data");
  params.set("source_type", "trace_project");
  if (observeId) params.set("source_id", observeId);
  return `/dashboard/evaluations/create?${params.toString()}`;
};

export const buildObserveRouteFocusPayload = ({ observeId, mode } = {}) => {
  const normalizedMode = modeSet.has(mode)
    ? mode
    : OBSERVE_ONBOARDING_MODES.SEND_FIRST_TRACE;
  const artifactId = safeKeyPart(observeId, DEFAULT_ARTIFACT_ID);

  return {
    eventName: "onboarding_observe_route_focus_viewed",
    primaryPath: "observe",
    stage: observeOnboardingStage(normalizedMode),
    source: "observe_project_onboarding",
    artifactType: "observe_project",
    artifactId,
    projectId: observeId,
    metadata: compactMetadata({
      project_id: observeId,
      route_mode: normalizedMode,
    }),
    idempotencyKey: [
      "onboarding_observe_route_focus_viewed",
      safeKeyPart(normalizedMode, "mode"),
      artifactId,
    ].join(":"),
    isSample: false,
  };
};
