export const TEST_ONBOARDING_MODES = {
  CREATE_EVAL: "create-eval",
  SAVE_EVAL: "save-eval",
};

export const isEvalOnboardingMode = (mode) =>
  mode === TEST_ONBOARDING_MODES.CREATE_EVAL ||
  mode === TEST_ONBOARDING_MODES.SAVE_EVAL;
