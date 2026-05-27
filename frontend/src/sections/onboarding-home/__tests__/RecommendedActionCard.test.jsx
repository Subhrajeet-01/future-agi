import { describe, expect, it, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import { render, screen } from "src/utils/test-utils";
import { getActivationStateFixture } from "../fixtures/activation-state.fixtures";
import { normalizeActivationState } from "../activation-state-utils";
import RecommendedActionCard from "../components/RecommendedActionCard";

const actionFixture = () =>
  normalizeActivationState(getActivationStateFixture("observeNoSetup"))
    .recommendedAction;

describe("RecommendedActionCard", () => {
  it("renders an available action as an internal link", async () => {
    const onActionClick = vi.fn();
    render(
      <RecommendedActionCard
        action={actionFixture()}
        label="Recommended action"
        onActionClick={onActionClick}
      />,
    );

    expect(
      screen.getByRole("link", { name: /connect observability/i }),
    ).toHaveAttribute(
      "href",
      "/dashboard/observe?setup=true&source=onboarding",
    );

    await userEvent.click(
      screen.getByRole("link", { name: /connect observability/i }),
    );
    expect(onActionClick).toHaveBeenCalledWith(
      expect.objectContaining({ id: "create_observe_project" }),
    );
  });

  it("disables blocked actions and shows the blocker", () => {
    const action = {
      ...actionFixture(),
      href: null,
      blocked: true,
      blockedReason: "route_not_implemented",
      routeAvailable: false,
    };

    render(
      <RecommendedActionCard action={action} label="Recommended action" />,
    );

    expect(screen.getByText("route not implemented")).toBeVisible();
    expect(
      screen.getByRole("button", { name: /connect observability/i }),
    ).toBeDisabled();
  });
});
