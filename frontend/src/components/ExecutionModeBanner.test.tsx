import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ExecutionModeBanner } from "./ExecutionModeBanner";

describe("ExecutionModeBanner", () => {
  it("always exposes paper mode and data sources", () => {
    render(
      <ExecutionModeBanner
        sources={{
          marketData: "PUBLIC",
          execution: "INTERNAL_PAPER",
          mode: "PAPER",
          futureBroker: "WEBULL",
        }}
      />,
    );
    expect(screen.getByText("Mode: PAPER")).toBeInTheDocument();
    expect(screen.getByText("Market Data: PUBLIC")).toBeInTheDocument();
  });
});
