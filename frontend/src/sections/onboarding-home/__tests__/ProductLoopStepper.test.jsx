import { describe, expect, it } from "vitest";
import { render, screen } from "src/utils/test-utils";
import ProductLoopStepper from "../components/ProductLoopStepper";

describe("ProductLoopStepper", () => {
  it("renders all product loop steps with normalized statuses", () => {
    render(
      <ProductLoopStepper
        progress={{
          build: "selected",
          observe: "complete",
        }}
      />,
    );

    expect(screen.getByText("Build")).toBeVisible();
    expect(screen.getByText("Test")).toBeVisible();
    expect(screen.getByText("Observe")).toBeVisible();
    expect(screen.getByText("Ship")).toBeVisible();
    expect(screen.getByText("Improve")).toBeVisible();
    expect(screen.getByText("selected")).toBeVisible();
    expect(screen.getByText("complete")).toBeVisible();
  });
});
