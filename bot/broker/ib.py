"""Interactive Brokers broker — implements BaseBroker via ib_insync.

Connects to TWS or IB Gateway. Use paper trading port 7497 (TWS) or 4002 (GW).

Requires: pip install ib_insync
"""

from __future__ import annotations

from typing import Optional
import structlog

from broker.base import BaseBroker, AccountInfo, Position

log = structlog.get_logger()


class IBBroker(BaseBroker):
    """Interactive Brokers connector via ib_insync."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,     # 7497 = TWS paper, 4002 = IB Gateway paper
        client_id: int = 1,
    ) -> None:
        try:
            from ib_insync import IB
        except ImportError as exc:
            raise ImportError(
                "ib_insync is required for IBBroker: pip install ib_insync"
            ) from exc

        self._ib = IB()
        self._host = host
        self._port = port
        self._client_id = client_id
        self._ib.connect(host, port, clientId=client_id)
        log.info("ib_broker.connected", host=host, port=port)

    def get_account(self) -> AccountInfo:
        values = {v.tag: v.value for v in self._ib.accountValues() if v.currency == "USD"}
        return AccountInfo(
            account_id=self._ib.managedAccounts()[0],
            equity=float(values.get("NetLiquidation", 0)),
            cash=float(values.get("CashBalance", 0)),
            buying_power=float(values.get("BuyingPower", 0)),
            portfolio_value=float(values.get("GrossPositionValue", 0)),
            is_paper=self._port in (7497, 4002),
        )

    def get_positions(self) -> list[Position]:
        return [
            Position(
                symbol=p.contract.symbol,
                qty=float(p.position),
                market_value=float(p.marketValue),
                unrealized_pl=float(p.unrealizedPNL),
                current_price=float(p.averageCost),  # IB doesn't give live price here
            )
            for p in self._ib.positions()
            if p.position != 0
        ]

    def get_position(self, symbol: str) -> Optional[Position]:
        for p in self.get_positions():
            if p.symbol == symbol:
                return p
        return None

    def place_market_order(self, symbol: str, qty: float, side: str) -> dict:
        from ib_insync import Stock, MarketOrder
        if side not in ("buy", "sell"):
            raise ValueError(f"Invalid side: {side!r}")

        contract = Stock(symbol, "SMART", "USD")
        order = MarketOrder(side.upper(), qty)
        trade = self._ib.placeOrder(contract, order)
        self._ib.sleep(1)  # Allow IB to fill order details
        log.info("ib.order.placed", symbol=symbol, qty=qty, side=side, status=trade.orderStatus.status)
        return {
            "order_id": trade.order.orderId,
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "status": trade.orderStatus.status,
        }

    def is_market_open(self) -> bool:
        from ib_insync import Stock
        contract = Stock("SPY", "SMART", "USD")
        details = self._ib.reqContractDetails(contract)
        if not details:
            return False
        # Check trading hours (simplified — always check via IB's market hours)
        return True

    def healthcheck(self) -> bool:
        return self._ib.isConnected()

    def disconnect(self) -> None:
        self._ib.disconnect()
        log.info("ib_broker.disconnected")
