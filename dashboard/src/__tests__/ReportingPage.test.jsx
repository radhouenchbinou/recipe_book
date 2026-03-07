import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// ── API mock ──────────────────────────────────────────────────────────────

const mockTrades = {
  rows: [
    {
      id: 1, order_id: "ord-001", broker: "alpaca-paper",
      symbol: "AAPL", side: "buy", qty: 10, status: "filled",
      filled_price: 150.0, error: null, source: "rebalance",
      created_at: "2026-03-01T12:00:00Z",
    },
    {
      id: 2, order_id: "ord-002", broker: "alpaca-paper",
      symbol: "SPY", side: "sell", qty: 5, status: "rejected",
      filled_price: null, error: "insufficient shares", source: "stop_loss",
      created_at: "2026-03-02T10:00:00Z",
    },
  ],
  summary: { total_orders: 2, filled_buys: 1, filled_sells: 0, rejected: 1 },
};

const mockPnl = {
  rows: [
    { symbol: "AAPL", total_bought: 1500, total_sold: 1650, realised_pl: 150, total_buy_qty: 10, total_sell_qty: 10 },
    { symbol: "SPY",  total_bought: 2000, total_sold: 1900, realised_pl: -100, total_buy_qty: 5,  total_sell_qty: 5 },
  ],
  summary: { symbols_traded: 2, total_realised_pl: 50 },
};

const mockAccuracy = {
  rows: [
    { source: "claude",   action: "buy",  total: 10, followed_by_trade: 4, pct_followed: 40 },
    { source: "fallback", action: "hold", total: 5,  followed_by_trade: 1, pct_followed: 20 },
  ],
  groups: 2,
};

vi.mock("../services/api.js", () => ({
  getReportTrades:   vi.fn().mockResolvedValue(mockTrades),
  getReportPnl:      vi.fn().mockResolvedValue(mockPnl),
  getReportAccuracy: vi.fn().mockResolvedValue(mockAccuracy),
  downloadReportCsv: vi.fn(),
}));

import ReportingPage from "../pages/ReportingPage.jsx";

// ── Helpers ────────────────────────────────────────────────────────────────

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ReportingPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe("ReportingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders page title", () => {
    renderPage();
    expect(screen.getByText("Reports")).toBeDefined();
  });

  it("renders all three tab buttons", () => {
    renderPage();
    expect(screen.getByText("Trade Log")).toBeDefined();
    expect(screen.getByText("Realised P&L")).toBeDefined();
    expect(screen.getByText("Rec. Accuracy")).toBeDefined();
  });

  it("shows Trade Log tab by default", () => {
    renderPage();
    // Summary pill labels are visible on trade log tab
    expect(screen.getByText("Total orders")).toBeDefined();
  });

  it("shows trade rows in the table", async () => {
    renderPage();
    await screen.findByText("AAPL");
    expect(screen.getByText("SPY")).toBeDefined();
  });

  it("shows filled buys / rejected counts in summary pills", async () => {
    renderPage();
    // pillVal values: 2, 1, 0, 1
    await screen.findByText("AAPL");
    expect(screen.getByText("Filled buys")).toBeDefined();
    expect(screen.getByText("Rejected")).toBeDefined();
  });

  it("shows source column", async () => {
    renderPage();
    await screen.findByText("rebalance");
    expect(screen.getByText("stop_loss")).toBeDefined();
  });

  it("switches to P&L tab on click", async () => {
    renderPage();
    fireEvent.click(screen.getByText("Realised P&L"));
    await screen.findByText("Symbols traded");
    expect(screen.getByText("Total realised P&L")).toBeDefined();
  });

  it("shows P&L rows with symbol names", async () => {
    renderPage();
    fireEvent.click(screen.getByText("Realised P&L"));
    await screen.findByText("AAPL");
    expect(screen.getByText("SPY")).toBeDefined();
  });

  it("switches to Accuracy tab on click", async () => {
    renderPage();
    fireEvent.click(screen.getByText("Rec. Accuracy"));
    await screen.findByText("claude");
    expect(screen.getByText("fallback")).toBeDefined();
  });

  it("shows pct_followed values in accuracy tab", async () => {
    renderPage();
    fireEvent.click(screen.getByText("Rec. Accuracy"));
    await screen.findByText("40%");
    expect(screen.getByText("20%")).toBeDefined();
  });

  it("renders period selector buttons", () => {
    renderPage();
    expect(screen.getByText("7d")).toBeDefined();
    expect(screen.getByText("30d")).toBeDefined();
    expect(screen.getByText("90d")).toBeDefined();
    expect(screen.getByText("1y")).toBeDefined();
  });

  it("renders CSV download button", () => {
    renderPage();
    expect(screen.getByText("⬇ CSV")).toBeDefined();
  });
});
