"""Backtesting engine — replays historical recommendations against price data.

Phase 2 / Sprint 1
Simulates portfolio performance by replaying past buy/sell/hold signals
against actual OHLCV data, producing equity curves and trade logs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional
import structlog
from sqlalchemy import text

from db import get_session

log = structlog.get_logger()


@dataclass
class Trade:
    date: date
    ticker: str
    action: str          # buy | sell
    price: float
    qty: float
    value: float
    signal_confidence: float
    source: str          # claude | fallback


@dataclass
class BacktestResult:
    ticker: str
    start_date: date
    end_date: date
    initial_capital: float
    final_value: float
    total_return_pct: float
    sharpe_ratio: Optional[float]
    max_drawdown_pct: float
    win_rate_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[dict] = field(default_factory=list)  # [{date, value}]


class BacktestEngine:
    """
    Replay historical recommendations against OHLCV data.

    Algorithm:
    1. Load all recommendations for the symbol in [start_date, end_date]
    2. For each recommendation date, fetch the next-day open price (execution price)
    3. Apply buy/sell signals with position sizing from recommendation confidence
    4. Track cash + holdings, compute daily portfolio value
    5. Compute performance metrics
    """

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        max_position_pct: float = 0.10,   # max 10% of portfolio per position
        commission_pct: float = 0.001,    # 0.1% per trade
    ) -> None:
        self.initial_capital = initial_capital
        self.max_position_pct = max_position_pct
        self.commission_pct = commission_pct

    def run(self, ticker: str, start_date: date, end_date: date) -> BacktestResult:
        """Run backtest for a single ticker over the given date range."""
        log.info("backtest.start", ticker=ticker, start=str(start_date), end=str(end_date))

        ohlcv = self._load_ohlcv(ticker, start_date, end_date)
        signals = self._load_signals(ticker, start_date, end_date)

        if not ohlcv:
            log.warning("backtest.no_data", ticker=ticker)
            return self._empty_result(ticker, start_date, end_date)

        result = self._simulate(ticker, ohlcv, signals, start_date, end_date)
        log.info(
            "backtest.done",
            ticker=ticker,
            total_return=result.total_return_pct,
            sharpe=result.sharpe_ratio,
            max_drawdown=result.max_drawdown_pct,
            trades=result.total_trades,
        )
        return result

    # ── Private helpers ────────────────────────────────────────────────────

    def _load_ohlcv(self, ticker: str, start: date, end: date) -> list[dict]:
        session = get_session()
        try:
            rows = session.execute(
                text("""
                    SELECT md.trade_date, md.open, md.high, md.low, md.close, md.volume
                    FROM   market_data md
                    JOIN   symbols s ON s.id = md.symbol_id
                    WHERE  s.ticker   = :ticker
                      AND  md.trade_date BETWEEN :start AND :end
                    ORDER  BY md.trade_date ASC
                """),
                {"ticker": ticker, "start": start, "end": end},
            ).fetchall()
            return [{"date": r[0], "open": float(r[1]), "high": float(r[2]),
                     "low": float(r[3]), "close": float(r[4]), "volume": int(r[5])}
                    for r in rows]
        finally:
            session.close()

    def _load_signals(self, ticker: str, start: date, end: date) -> list[dict]:
        session = get_session()
        try:
            rows = session.execute(
                text("""
                    SELECT r.recommended_at::date AS signal_date,
                           r.action, r.confidence, r.source
                    FROM   recommendations r
                    JOIN   symbols s ON s.id = r.symbol_id
                    WHERE  s.ticker = :ticker
                      AND  r.recommended_at::date BETWEEN :start AND :end
                    ORDER  BY r.recommended_at ASC
                """),
                {"ticker": ticker, "start": start, "end": end},
            ).fetchall()
            return [{"date": r[0], "action": r[1], "confidence": float(r[2]), "source": r[3]}
                    for r in rows]
        finally:
            session.close()

    def _simulate(
        self,
        ticker: str,
        ohlcv: list[dict],
        signals: list[dict],
        start_date: date,
        end_date: date,
    ) -> BacktestResult:
        # Index prices by date for O(1) lookup
        price_by_date = {row["date"]: row for row in ohlcv}
        signal_by_date = {s["date"]: s for s in signals}

        cash = self.initial_capital
        shares = 0.0
        trades: list[Trade] = []
        equity_curve: list[dict] = []
        peak_value = self.initial_capital

        for i, day in enumerate(ohlcv):
            d = day["date"]
            price = day["close"]
            portfolio_value = cash + shares * price

            # Track peak for drawdown
            peak_value = max(peak_value, portfolio_value)

            equity_curve.append({"date": str(d), "value": round(portfolio_value, 2)})

            # Execute signal from previous day (next-day open execution)
            signal = signal_by_date.get(d)
            if signal and i + 1 < len(ohlcv):
                exec_price = ohlcv[i + 1]["open"]  # next day open
                action = signal["action"]
                conf = signal["confidence"]

                if action == "buy" and shares == 0:
                    max_value = portfolio_value * self.max_position_pct * (1 + conf)
                    max_value = min(max_value, cash * 0.95)
                    qty = max_value / exec_price
                    cost = qty * exec_price * (1 + self.commission_pct)
                    if cost <= cash and qty > 0:
                        cash -= cost
                        shares += qty
                        trades.append(Trade(
                            date=ohlcv[i + 1]["date"], ticker=ticker,
                            action="buy", price=exec_price, qty=qty,
                            value=cost, signal_confidence=conf,
                            source=signal["source"],
                        ))

                elif action == "sell" and shares > 0:
                    proceeds = shares * exec_price * (1 - self.commission_pct)
                    cash += proceeds
                    trades.append(Trade(
                        date=ohlcv[i + 1]["date"], ticker=ticker,
                        action="sell", price=exec_price, qty=shares,
                        value=proceeds, signal_confidence=conf,
                        source=signal["source"],
                    ))
                    shares = 0.0

        # Close any open position at end
        if shares > 0 and ohlcv:
            final_price = ohlcv[-1]["close"]
            cash += shares * final_price * (1 - self.commission_pct)
            shares = 0.0

        final_value = cash
        total_return_pct = (final_value - self.initial_capital) / self.initial_capital * 100

        # Compute max drawdown from equity curve
        max_drawdown = self._max_drawdown(equity_curve)

        # Win rate
        buy_trades = [t for t in trades if t.action == "buy"]
        sell_trades = [t for t in trades if t.action == "sell"]
        winning = sum(1 for b, s in zip(buy_trades, sell_trades) if s.value > b.value)
        total_pairs = min(len(buy_trades), len(sell_trades))
        win_rate = (winning / total_pairs * 100) if total_pairs > 0 else 0.0

        # Sharpe ratio (annualised, daily returns)
        sharpe = self._sharpe(equity_curve)

        return BacktestResult(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_value=round(final_value, 2),
            total_return_pct=round(total_return_pct, 2),
            sharpe_ratio=sharpe,
            max_drawdown_pct=round(max_drawdown, 2),
            win_rate_pct=round(win_rate, 2),
            total_trades=len(trades),
            winning_trades=winning,
            losing_trades=total_pairs - winning,
            trades=trades,
            equity_curve=equity_curve,
        )

    @staticmethod
    def _max_drawdown(equity_curve: list[dict]) -> float:
        if not equity_curve:
            return 0.0
        peak = equity_curve[0]["value"]
        max_dd = 0.0
        for point in equity_curve:
            v = point["value"]
            peak = max(peak, v)
            dd = (peak - v) / peak * 100
            max_dd = max(max_dd, dd)
        return max_dd

    @staticmethod
    def _sharpe(equity_curve: list[dict], risk_free_daily: float = 0.0001) -> Optional[float]:
        if len(equity_curve) < 2:
            return None
        values = [p["value"] for p in equity_curve]
        returns = [(values[i] - values[i - 1]) / values[i - 1] for i in range(1, len(values))]
        if not returns:
            return None
        import statistics
        mean_r = statistics.mean(returns) - risk_free_daily
        std_r = statistics.stdev(returns) if len(returns) > 1 else 0
        if std_r == 0:
            return None
        return round(mean_r / std_r * (252 ** 0.5), 3)  # annualised

    def _empty_result(self, ticker: str, start: date, end: date) -> BacktestResult:
        return BacktestResult(
            ticker=ticker, start_date=start, end_date=end,
            initial_capital=self.initial_capital, final_value=self.initial_capital,
            total_return_pct=0.0, sharpe_ratio=None, max_drawdown_pct=0.0,
            win_rate_pct=0.0, total_trades=0, winning_trades=0, losing_trades=0,
        )
