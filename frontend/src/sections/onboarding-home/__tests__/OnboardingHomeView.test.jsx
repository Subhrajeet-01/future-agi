import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "src/utils/test-utils";
import userEvent from "@testing-library/user-event";
import { renderWithRouter } from "src/utils/test-utils";
import { getActivationStateFixture } from "../fixtures/activation-state.fixtures";
import { normalizeActivationState } from "../activation-state-utils";
import OnboardingHomeView from "../OnboardingHomeView";

const mocks = vi.hoisted(() => ({
  useActivationState: vi.fn(),
  useAuthContext: vi.fn(),
  useWorkspace: vi.fn(),
}));

vi.mock("../hooks/useActivationState", () => ({
  useActivationState: (params) => mocks.useActivationState(params),
}));

vi.mock("src/auth/hooks", () => ({
  useAuthContext: () => mocks.useAuthContext(),
}));

vi.mock("src/contexts/WorkspaceContext", () => ({
  useWorkspace: () => mocks.useWorkspace(),
}));

const defaultUser = {
  id: "usr_onboarding",
  default_workspace_id: "wrk_onboarding",
  organization: {
    id: "org_onboarding",
  },
};

const defaultWorkspace = {
  currentWorkspaceId: "wrk_onboarding",
  currentWorkspaceDisplayName: "Quality Workspace",
  isReady: true,
};

const normalizedFixture = (name) =>
  normalizeActivationState(getActivationStateFixture(name));

const renderView = (route = "/dashboard/home") =>
  renderWithRouter(<OnboardingHomeView />, { route });

describe("OnboardingHomeView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.useAuthContext.mockReturnValue({ user: defaultUser });
    mocks.useWorkspace.mockReturnValue(defaultWorkspace);
  });

  it("renders the route skeleton while activation state is loading", () => {
    mocks.useActivationState.mockReturnValue({
      state: null,
      isLoading: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    renderView();

    expect(screen.getByTestId("onboarding-home-skeleton")).toBeInTheDocument();
  });

  it("falls back to Get Started when onboarding home is feature disabled", () => {
    mocks.useActivationState.mockReturnValue({
      state: normalizedFixture("featureDisabled"),
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    renderView();

    expect(screen.getByText("Start with the setup checklist")).toBeVisible();
    expect(screen.getAllByText("Open Get Started").length).toBeGreaterThan(0);
    expect(
      screen.getByText(
        "The existing setup checklist is available for this workspace.",
      ),
    ).toBeVisible();
  });

  it("renders the recommended first action from activation state", () => {
    mocks.useActivationState.mockReturnValue({
      state: normalizedFixture("newWorkspaceNoGoal"),
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    renderView("/dashboard/home?source=email&campaign_key=welcome");

    expect(screen.getByText("Choose what to set up first")).toBeVisible();
    expect(screen.getByText("Choose your first goal")).toBeVisible();
    expect(screen.getByText("Workspace: Quality Workspace")).toBeVisible();
    expect(mocks.useActivationState).toHaveBeenCalledWith(
      expect.objectContaining({
        organizationId: "org_onboarding",
        workspaceId: "wrk_onboarding",
        source: "email",
        campaignKey: "welcome",
      }),
    );
  });

  it("renders a hard-error fallback and retries on demand", async () => {
    const refetch = vi.fn();
    mocks.useActivationState.mockReturnValue({
      state: null,
      isLoading: false,
      isError: true,
      error: { message: "Activation state failed" },
      refetch,
    });

    renderView();

    expect(screen.getByTestId("onboarding-home-error")).toBeInTheDocument();
    expect(screen.getByText("Activation state failed")).toBeVisible();
    expect(screen.getByRole("link", { name: /get started/i })).toHaveAttribute(
      "href",
      "/dashboard/get-started",
    );

    await userEvent.click(screen.getByRole("button", { name: /retry/i }));

    expect(refetch).toHaveBeenCalledTimes(1);
  });
});
