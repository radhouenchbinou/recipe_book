import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("../services/api.js", () => ({
  getRecommendations: vi.fn().mockResolvedValue({
    data: [
      {
        id: "1",
        ticker: "AAPL",
        action: "buy",
        confidence: 0.82,
        reasoning: "RSI oversold with bullish MACD crossover.",
        source: "claude",
        recommended_at: "2024-01-10T18:45:00Z",
      },
    ],
    meta: { total: 1 },
  }),
}));

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <RecommendationsPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

import RecommendationsPage from "../pages/RecommendationsPage.jsx";

describe("RecommendationsPage", () => {
  it("renders page title", async () => {
    renderPage();
    expect(screen.getByText("Recommendations")).toBeDefined();
  });

  it("displays ticker and action from API data", async () => {
    renderPage();
    await screen.findByText("AAPL");
    expect(screen.getByText("BUY")).toBeDefined();
  });

  it("displays reasoning text", async () => {
    renderPage();
    await screen.findByText(/RSI oversold/i);
  });
});
