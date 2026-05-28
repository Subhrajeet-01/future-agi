import { describe, expect, it } from "vitest";
import {
  buildObserveEvaluatorCreateHref,
  buildObserveProjectOnboardingHref,
  buildObserveRouteFocusPayload,
  getObserveOnboardingCopy,
  getObserveOnboardingParams,
  observeOnboardingStage,
  OBSERVE_ONBOARDING_MODES,
} from "./observeOnboardingRoute";

describe("observeOnboardingRoute", () => {
  it("reads supported observe route params", () => {
    expect(
      getObserveOnboardingParams(
        "?source=onboarding&onboarding=send-first-trace",
      ),
    ).toEqual({
      isOnboarding: true,
      mode: OBSERVE_ONBOARDING_MODES.SEND_FIRST_TRACE,
    });
  });

  it("drops unsupported modes", () => {
    expect(
      getObserveOnboardingParams("?source=onboarding&onboarding=unknown"),
    ).toEqual({
      isOnboarding: true,
      mode: null,
    });
  });

  it("builds observe project route-mode hrefs", () => {
    expect(
      buildObserveProjectOnboardingHref({
        observeId: "project-1",
        mode: OBSERVE_ONBOARDING_MODES.CREATE_EVALUATOR,
      }),
    ).toBe(
      "/dashboard/observe/project-1/llm-tracing?source=onboarding&onboarding=create-evaluator",
    );
  });

  it("builds eval creation hrefs from an observe project", () => {
    expect(buildObserveEvaluatorCreateHref({ observeId: "project-1" })).toBe(
      "/dashboard/evaluations/create?source=onboarding&step=data&source_type=trace_project&source_id=project-1",
    );
  });

  it("maps modes to activation stages", () => {
    expect(
      observeOnboardingStage(OBSERVE_ONBOARDING_MODES.CREATE_EVALUATOR),
    ).toBe("create_trace_evaluator");
    expect(
      observeOnboardingStage(OBSERVE_ONBOARDING_MODES.SEND_FIRST_TRACE),
    ).toBe("waiting_for_first_trace");
  });

  it("returns mode-specific panel copy", () => {
    expect(
      getObserveOnboardingCopy(OBSERVE_ONBOARDING_MODES.SEND_FIRST_TRACE),
    ).toMatchObject({
      currentStep: "First trace",
      primaryLabel: "Refresh traces",
      title: "Send the first trace",
    });
  });

  it("builds a safe route-focus payload", () => {
    expect(
      buildObserveRouteFocusPayload({
        observeId: "project-1",
        mode: OBSERVE_ONBOARDING_MODES.CREATE_EVALUATOR,
      }),
    ).toMatchObject({
      eventName: "onboarding_observe_route_focus_viewed",
      primaryPath: "observe",
      stage: "create_trace_evaluator",
      source: "observe_project_onboarding",
      artifactType: "observe_project",
      artifactId: "project-1",
      projectId: "project-1",
      metadata: {
        project_id: "project-1",
        route_mode: "create-evaluator",
      },
      idempotencyKey:
        "onboarding_observe_route_focus_viewed:create-evaluator:project-1",
      isSample: false,
    });
  });
});
