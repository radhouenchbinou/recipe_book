import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import LoginPage from "../pages/LoginPage.jsx";

// Mock useAuth
vi.mock("../hooks/useAuth.js", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "../hooks/useAuth.js";

function renderLogin(authOverrides = {}) {
  const defaults = { login: vi.fn().mockResolvedValue(false), error: null, loading: false };
  useAuth.mockReturnValue({ ...defaults, ...authOverrides });
  return render(<MemoryRouter><LoginPage /></MemoryRouter>);
}

describe("LoginPage", () => {
  it("renders username and password inputs", () => {
    renderLogin();
    expect(screen.getByPlaceholderText("Username")).toBeDefined();
    expect(screen.getByPlaceholderText("Password")).toBeDefined();
  });

  it("calls login with entered credentials on submit", async () => {
    const loginFn = vi.fn().mockResolvedValue(false);
    renderLogin({ login: loginFn });

    fireEvent.change(screen.getByPlaceholderText("Username"), { target: { value: "admin" } });
    fireEvent.change(screen.getByPlaceholderText("Password"), { target: { value: "pass" } });
    fireEvent.submit(screen.getByRole("button"));

    await waitFor(() => expect(loginFn).toHaveBeenCalledWith("admin", "pass"));
  });

  it("displays error message when auth error is set", () => {
    renderLogin({ error: "Invalid credentials" });
    expect(screen.getByText("Invalid credentials")).toBeDefined();
  });

  it("shows loading state on button", () => {
    renderLogin({ loading: true });
    expect(screen.getByRole("button").textContent).toContain("Signing in");
  });
});
