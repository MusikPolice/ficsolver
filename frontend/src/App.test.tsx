import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import App from "./App";

describe("App", () => {
  it("renders the placeholder text", () => {
    render(<App />);
    expect(screen.getByText(/ficsolver/i)).toBeInTheDocument();
  });
});
