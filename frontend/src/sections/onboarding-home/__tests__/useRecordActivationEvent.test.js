import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useRecordActivationEvent } from "../hooks/useRecordActivationEvent";
import { recordActivationEvent } from "../api/onboarding-home-api";
import { trackOnboardingHomeEvent } from "../analytics/onboarding-events";

vi.mock("../api/onboarding-home-api", () => ({
  onboardingHomeQueryKeys: {
    all: ["onboarding-home"],
  },
  recordActivationEvent: vi.fn(),
}));

vi.mock("../analytics/onboarding-events", () => ({
  OnboardingHomeEvents: {
    activationEventRecorded: "onboarding_activation_event_recorded",
  },
  trackOnboardingHomeEvent: vi.fn(),
}));

const renderWithQueryClient = (hook) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
  const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
  const wrapper = ({ children }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);

  return {
    ...renderHook(hook, { wrapper }),
    invalidateQueries,
  };
};

describe("useRecordActivationEvent", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("tracks successful activation events through onboarding analytics", async () => {
    recordActivationEvent.mockResolvedValueOnce({
      requestId: "req-next",
      stage: "review_eval_failures",
      primaryPath: "evals",
      isActivated: false,
      workspaceId: "wrk-1",
      organizationId: "org-1",
      userId: "usr-1",
    });

    const { result, invalidateQueries } = renderWithQueryClient(() =>
      useRecordActivationEvent(),
    );

    await act(async () => {
      await result.current.mutateAsync({
        eventName: "eval_run_completed",
        primaryPath: "evals",
        stage: "run_eval",
        source: "eval_create_page",
        artifactType: "eval",
        artifactId: "eval-1",
        projectId: "project-1",
        isSample: false,
        metadata: {
          prompt: "do not forward",
        },
        idempotencyKey: "dedupe-key",
      });
    });

    expect(recordActivationEvent).toHaveBeenCalledWith({
      eventName: "eval_run_completed",
      primaryPath: "evals",
      stage: "run_eval",
      source: "eval_create_page",
      artifactType: "eval",
      artifactId: "eval-1",
      projectId: "project-1",
      isSample: false,
      metadata: {
        prompt: "do not forward",
      },
      idempotencyKey: "dedupe-key",
    });
    expect(trackOnboardingHomeEvent).toHaveBeenCalledWith(
      "onboarding_activation_event_recorded",
      {
        activation_event_name: "eval_run_completed",
        primary_path: "evals",
        activation_stage: "run_eval",
        source: "eval_create_page",
        artifact_type: "eval",
        artifact_id: "eval-1",
        project_id: "project-1",
        is_sample: false,
        next_stage: "review_eval_failures",
        next_primary_path: "evals",
        next_is_activated: false,
        next_request_id: "req-next",
        workspace_id: "wrk-1",
        organization_id: "org-1",
        user_id: "usr-1",
      },
    );
    expect(trackOnboardingHomeEvent.mock.calls[0][1]).not.toHaveProperty(
      "metadata",
    );
    expect(trackOnboardingHomeEvent.mock.calls[0][1]).not.toHaveProperty(
      "idempotency_key",
    );
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["onboarding-home"],
    });
  });

  it("does not track failed activation event mutations", async () => {
    recordActivationEvent.mockRejectedValueOnce(new Error("failed"));

    const { result } = renderWithQueryClient(() => useRecordActivationEvent());

    await act(async () => {
      await expect(
        result.current.mutateAsync({
          event_name: "voice_agent_created",
          primary_path: "voice",
          stage: "create_voice_agent",
        }),
      ).rejects.toThrow("failed");
    });

    await waitFor(() => {
      expect(trackOnboardingHomeEvent).not.toHaveBeenCalled();
    });
  });
});
