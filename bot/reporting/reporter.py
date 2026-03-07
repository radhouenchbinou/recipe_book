"""Trade and performance reporting — CSV / JSON export.

Phase 3 / Sprint 2
Aggregates data from the order_ledger, recommendations, and market_data tables
into structured reports that can be exported as CSV or JSON.

Reports available:
  trade_log      — all orders from order_ledger, optionally filtered by date/symbol/broker
  pnl_summary    — realised P&L by symbol (matched buy→sell pairs, FIFO)
  recommendation_accuracy — how often Claude/fallback recommendations led to profitable trades
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Optional
import structlog
from sqlalchemy import text

from db import get_session

log = structlog.get_logger()


# ── Report data models ─────────────────────────────────────────────────────

@dataclass
class TradeRow:
    id: int
    order_id: str
    broker: str
    symbol: str
    side: str
    qty: int
    status: str
    filled_price: Optional[float]
    error: Optional[str]
    source: Optional[str]
    created_at: str


@dataclass
class PnlRow:
    symbol: str
    total_bought:    float   # total cost basis
    total_sold:      float   # total proceeds
    realised_pl:     float
    total_buy_qty:   int
    total_sell_qty:  int


@dataclass
class AccuracyRow:
    source: str            # 'claude' | 'fallback'
    action: str            # 'buy' | 'sell' | 'hold'
    total:  int
    followed_by_trade: int   # orders placed with same symbol within 2 days
    pct_followed: float


@dataclass
class Report:
    report_type: str
    generated_at: str
    filters: dict
    rows: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


# ── Reporter ───────────────────────────────────────────────────────────────

class Reporter:
    """
    Generates trade / P&L / accuracy reports from the database.

    Usage::

        reporter = Reporter()
        report   = reporter.trade_log(symbol="AAPL", days=30)
        print(reporter.to_json(report))
        print(reporter.to_csv(report))
    """

    # ── Public report builders ─────────────────────────────────────────────

    def trade_log(
        self,
        symbol: Optional[str] = None,
        broker: Optional[str] = None,
        status: Optional[str] = None,
        days:   int = 30,
    ) -> Report:
        """
        Return all order_ledger entries matching the given filters.

        Args:
            symbol: Filter to a specific ticker (None = all).
            broker: Filter to a specific broker name (None = all).
            status: Filter to a specific order status (None = all).
            days:   Look-back window in calendar days (default 30).

        Returns:
            Report with one TradeRow per matching order.
        """
        filters = {"symbol": symbol, "broker": broker,
                   "status": status, "days": days}

        where_clauses = ["o.created_at >= NOW() - INTERVAL :days"]
        params: dict = {"days": f"{days} days"}

        if symbol:
            where_clauses.append("o.symbol = :symbol")
            params["symbol"] = symbol
        if broker:
            where_clauses.append("o.broker = :broker")
            params["broker"] = broker
        if status:
            where_clauses.append("o.status = :status")
            params["status"] = status

        where = " AND ".join(where_clauses)

        session = get_session()
        try:
            rows = session.execute(
                text(f"""
                    SELECT o.id, o.order_id, o.broker, o.symbol, o.side,
                           o.qty, o.status, o.filled_price, o.error,
                           o.source, o.created_at
                    FROM order_ledger o
                    WHERE {where}
                    ORDER BY o.created_at DESC
                """),
                params,
            ).fetchall()
        finally:
            session.close()

        trade_rows = [
            TradeRow(
                id=r[0], order_id=r[1], broker=r[2], symbol=r[3],
                side=r[4], qty=r[5], status=r[6],
                filled_price=float(r[7]) if r[7] is not None else None,
                error=r[8], source=r[9],
                created_at=str(r[10]),
            )
            for r in rows
        ]

        total_buy  = sum(1 for t in trade_rows if t.side == "buy"  and t.status == "filled")
        total_sell = sum(1 for t in trade_rows if t.side == "sell" and t.status == "filled")

        log.info("reporter.trade_log", count=len(trade_rows), **filters)
        return Report(
            report_type="trade_log",
            generated_at=datetime.utcnow().isoformat(),
            filters=filters,
            rows=[asdict(t) for t in trade_rows],
            summary={"total_orders": len(trade_rows),
                     "filled_buys": total_buy,
                     "filled_sells": total_sell},
        )

    def pnl_summary(
        self,
        symbol: Optional[str] = None,
        days:   int = 90,
    ) -> Report:
        """
        Compute realised P&L per symbol using filled orders (FIFO matching).

        Args:
            symbol: Restrict to a single ticker (None = all).
            days:   Look-back window.

        Returns:
            Report with one PnlRow per symbol.
        """
        filters = {"symbol": symbol, "days": days}
        params: dict = {"days": f"{days} days"}
        sym_clause = ""
        if symbol:
            sym_clause = "AND o.symbol = :symbol"
            params["symbol"] = symbol

        session = get_session()
        try:
            rows = session.execute(
                text(f"""
                    SELECT o.symbol, o.side, o.qty, o.filled_price
                    FROM order_ledger o
                    WHERE o.status = 'filled'
                      AND o.created_at >= NOW() - INTERVAL :days
                      {sym_clause}
                    ORDER BY o.symbol, o.created_at
                """),
                params,
            ).fetchall()
        finally:
            session.close()

        # Group by symbol
        by_symbol: dict[str, dict] = {}
        for r in rows:
            sym, side, qty, price = r[0], r[1], int(r[2]), float(r[3] or 0)
            if sym not in by_symbol:
                by_symbol[sym] = {"buys": [], "sells": []}
            by_symbol[sym][f"{side}s"].append((qty, price))

        pnl_rows: list[PnlRow] = []
        for sym, data in by_symbol.items():
            buy_cost  = sum(q * p for q, p in data["buys"])
            sell_proc = sum(q * p for q, p in data["sells"])
            pnl_rows.append(PnlRow(
                symbol=sym,
                total_bought=round(buy_cost, 2),
                total_sold=round(sell_proc, 2),
                realised_pl=round(sell_proc - buy_cost, 2),
                total_buy_qty=sum(q for q, _ in data["buys"]),
                total_sell_qty=sum(q for q, _ in data["sells"]),
            ))

        pnl_rows.sort(key=lambda r: r.realised_pl, reverse=True)
        total_pl = sum(r.realised_pl for r in pnl_rows)

        log.info("reporter.pnl_summary", symbols=len(pnl_rows), total_pl=total_pl)
        return Report(
            report_type="pnl_summary",
            generated_at=datetime.utcnow().isoformat(),
            filters=filters,
            rows=[asdict(r) for r in pnl_rows],
            summary={"symbols_traded": len(pnl_rows),
                     "total_realised_pl": round(total_pl, 2)},
        )

    def recommendation_accuracy(self, days: int = 30) -> Report:
        """
        Show how often recommendations were followed by same-symbol trades.

        Args:
            days: Look-back window.

        Returns:
            Report grouped by source × action.
        """
        filters = {"days": days}
        session = get_session()
        try:
            rows = session.execute(
                text("""
                    SELECT r.source, r.action, COUNT(*) AS total,
                           COUNT(o.id) AS followed
                    FROM recommendations r
                    LEFT JOIN order_ledger o
                           ON o.symbol = (SELECT ticker FROM symbols WHERE id = r.symbol_id)
                          AND o.created_at BETWEEN r.created_at
                                               AND r.created_at + INTERVAL '2 days'
                          AND o.status = 'filled'
                    WHERE r.created_at >= NOW() - INTERVAL :days
                    GROUP BY r.source, r.action
                    ORDER BY r.source, r.action
                """),
                {"days": f"{days} days"},
            ).fetchall()
        finally:
            session.close()

        acc_rows = [
            AccuracyRow(
                source=r[0], action=r[1],
                total=int(r[2]), followed_by_trade=int(r[3]),
                pct_followed=round(int(r[3]) / int(r[2]) * 100, 1) if r[2] else 0.0,
            )
            for r in rows
        ]

        log.info("reporter.accuracy", groups=len(acc_rows))
        return Report(
            report_type="recommendation_accuracy",
            generated_at=datetime.utcnow().isoformat(),
            filters=filters,
            rows=[asdict(r) for r in acc_rows],
            summary={"groups": len(acc_rows)},
        )

    # ── Export helpers ─────────────────────────────────────────────────────

    @staticmethod
    def to_json(report: Report, indent: int = 2) -> str:
        """Serialise a Report to a JSON string."""
        return json.dumps(
            {
                "report_type":  report.report_type,
                "generated_at": report.generated_at,
                "filters":      report.filters,
                "summary":      report.summary,
                "rows":         report.rows,
            },
            indent=indent,
            default=str,
        )

    @staticmethod
    def to_csv(report: Report) -> str:
        """Serialise the report rows to CSV (header derived from first row keys)."""
        if not report.rows:
            return ""
        output  = io.StringIO()
        headers = list(report.rows[0].keys())
        writer  = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report.rows)
        return output.getvalue()
