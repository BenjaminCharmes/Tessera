import { render, screen } from "@testing-library/react";
import App from "./App.tsx";

describe("App", () => {
  it("renders the application title", () => {
    render(<App />);
    expect(
      screen.getByRole("heading", { name: "{{project_name}}" }),
    ).toBeInTheDocument();
  });
});
