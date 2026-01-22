"""
CryptoBrain V2 - 데이터베이스 매니저
SQLite를 사용한 CRUD 연산
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from .models import (
    InvestorProfile,
    Position,
    PortfolioSummary,
    TradeHistory,
    WatchlistItem,
)


class DBManager:
    """SQLite 데이터베이스 관리자"""

    def __init__(self, db_path: str = "cryptobrain.db"):
        """
        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = Path(db_path)
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """컨텍스트 매니저를 통한 데이터베이스 연결"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_database(self):
        """데이터베이스 테이블 초기화"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 투자자 프로필 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS investor_profile (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_capital INTEGER NOT NULL DEFAULT 1000000,
                    monthly_income INTEGER DEFAULT 0,
                    investment_goal TEXT DEFAULT '장기자산증식',
                    investment_horizon TEXT DEFAULT '1-6개월',
                    max_loss_tolerance REAL DEFAULT 0.1,
                    risk_per_trade REAL DEFAULT 0.02,
                    risk_tolerance TEXT DEFAULT 'moderate',
                    preferred_volatility TEXT DEFAULT 'medium',
                    leverage_allowed INTEGER DEFAULT 0,
                    trading_style TEXT DEFAULT 'swing',
                    trading_frequency TEXT DEFAULT 'weekly',
                    preferred_session TEXT DEFAULT 'asia',
                    available_time_per_day INTEGER DEFAULT 30,
                    active_hours_start TEXT DEFAULT '09:00',
                    active_hours_end TEXT DEFAULT '23:00',
                    experience_years REAL DEFAULT 1.0,
                    technical_analysis_skill TEXT DEFAULT 'beginner',
                    past_major_mistakes TEXT DEFAULT '[]',
                    preferred_coins TEXT DEFAULT '["BTC", "ETH"]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 포지션 (보유 종목) 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL UNIQUE,
                    quantity REAL DEFAULT 0,
                    avg_entry_price REAL DEFAULT 0,
                    current_price REAL DEFAULT 0,
                    first_buy_date TIMESTAMP,
                    last_buy_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 현금 잔고 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cash_balance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    balance REAL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 매매 이력 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL DEFAULT 0,
                    price REAL DEFAULT 0,
                    timestamp TIMESTAMP,
                    market_condition TEXT DEFAULT 'sideways',
                    trigger_reason TEXT DEFAULT '본인판단',
                    emotional_state TEXT DEFAULT '침착',
                    pnl REAL,
                    pnl_pct REAL,
                    holding_period INTEGER,
                    related_trade_id INTEGER,
                    tags TEXT DEFAULT '[]',
                    notes TEXT DEFAULT '',
                    ai_recommendation TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 관심 코인 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL UNIQUE,
                    alert_conditions TEXT DEFAULT '{}',
                    notes TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    # ==================== Profile CRUD ====================

    def get_profile(self) -> Optional[InvestorProfile]:
        """투자자 프로필 조회 (첫 번째 프로필 반환)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM investor_profile ORDER BY id LIMIT 1")
            row = cursor.fetchone()

            if row:
                data = dict(row)
                data["leverage_allowed"] = bool(data.get("leverage_allowed", 0))
                return InvestorProfile.from_dict(data)
            return None

    def save_profile(self, profile: InvestorProfile) -> bool:
        """투자자 프로필 저장 (upsert)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 기존 프로필 확인
            cursor.execute("SELECT id FROM investor_profile ORDER BY id LIMIT 1")
            existing = cursor.fetchone()

            data = profile.to_dict()
            data["past_major_mistakes"] = json.dumps(data["past_major_mistakes"])
            data["preferred_coins"] = json.dumps(data["preferred_coins"])
            data["leverage_allowed"] = 1 if data["leverage_allowed"] else 0

            if existing:
                # 업데이트
                cursor.execute("""
                    UPDATE investor_profile SET
                        total_capital = ?,
                        monthly_income = ?,
                        investment_goal = ?,
                        investment_horizon = ?,
                        max_loss_tolerance = ?,
                        risk_per_trade = ?,
                        risk_tolerance = ?,
                        preferred_volatility = ?,
                        leverage_allowed = ?,
                        trading_style = ?,
                        trading_frequency = ?,
                        preferred_session = ?,
                        available_time_per_day = ?,
                        active_hours_start = ?,
                        active_hours_end = ?,
                        experience_years = ?,
                        technical_analysis_skill = ?,
                        past_major_mistakes = ?,
                        preferred_coins = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (
                    data["total_capital"],
                    data["monthly_income"],
                    data["investment_goal"],
                    data["investment_horizon"],
                    data["max_loss_tolerance"],
                    data["risk_per_trade"],
                    data["risk_tolerance"],
                    data["preferred_volatility"],
                    data["leverage_allowed"],
                    data["trading_style"],
                    data["trading_frequency"],
                    data["preferred_session"],
                    data["available_time_per_day"],
                    data["active_hours_start"],
                    data["active_hours_end"],
                    data["experience_years"],
                    data["technical_analysis_skill"],
                    data["past_major_mistakes"],
                    data["preferred_coins"],
                    datetime.now(),
                    existing["id"],
                ))
            else:
                # 새로 생성
                cursor.execute("""
                    INSERT INTO investor_profile (
                        total_capital, monthly_income, investment_goal, investment_horizon,
                        max_loss_tolerance, risk_per_trade, risk_tolerance, preferred_volatility,
                        leverage_allowed, trading_style, trading_frequency, preferred_session,
                        available_time_per_day, active_hours_start, active_hours_end,
                        experience_years, technical_analysis_skill, past_major_mistakes, preferred_coins
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data["total_capital"],
                    data["monthly_income"],
                    data["investment_goal"],
                    data["investment_horizon"],
                    data["max_loss_tolerance"],
                    data["risk_per_trade"],
                    data["risk_tolerance"],
                    data["preferred_volatility"],
                    data["leverage_allowed"],
                    data["trading_style"],
                    data["trading_frequency"],
                    data["preferred_session"],
                    data["available_time_per_day"],
                    data["active_hours_start"],
                    data["active_hours_end"],
                    data["experience_years"],
                    data["technical_analysis_skill"],
                    data["past_major_mistakes"],
                    data["preferred_coins"],
                ))

            return True

    # ==================== Position CRUD ====================

    def get_positions(self) -> list[Position]:
        """모든 포지션 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM positions WHERE quantity > 0 ORDER BY symbol")
            rows = cursor.fetchall()
            return [Position.from_dict(dict(row)) for row in rows]

    def get_position(self, symbol: str) -> Optional[Position]:
        """특정 포지션 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM positions WHERE symbol = ?", (symbol,))
            row = cursor.fetchone()
            return Position.from_dict(dict(row)) if row else None

    def save_position(self, position: Position) -> bool:
        """포지션 저장 (upsert)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM positions WHERE symbol = ?", (position.symbol,))
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE positions SET
                        quantity = ?,
                        avg_entry_price = ?,
                        current_price = ?,
                        first_buy_date = ?,
                        last_buy_date = ?,
                        updated_at = ?
                    WHERE symbol = ?
                """, (
                    position.quantity,
                    position.avg_entry_price,
                    position.current_price,
                    position.first_buy_date,
                    position.last_buy_date,
                    datetime.now(),
                    position.symbol,
                ))
            else:
                cursor.execute("""
                    INSERT INTO positions (
                        symbol, quantity, avg_entry_price, current_price,
                        first_buy_date, last_buy_date
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    position.symbol,
                    position.quantity,
                    position.avg_entry_price,
                    position.current_price,
                    position.first_buy_date,
                    position.last_buy_date,
                ))

            return True

    def delete_position(self, symbol: str) -> bool:
        """포지션 삭제"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
            return cursor.rowcount > 0

    def update_position_price(self, symbol: str, current_price: float) -> bool:
        """포지션 현재가 업데이트"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE positions SET current_price = ?, updated_at = ?
                WHERE symbol = ?
            """, (current_price, datetime.now(), symbol))
            return cursor.rowcount > 0

    # ==================== Cash Balance ====================

    def get_cash_balance(self) -> float:
        """현금 잔고 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM cash_balance ORDER BY id LIMIT 1")
            row = cursor.fetchone()
            return row["balance"] if row else 0.0

    def set_cash_balance(self, balance: float) -> bool:
        """현금 잔고 설정"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM cash_balance ORDER BY id LIMIT 1")
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE cash_balance SET balance = ?, updated_at = ?
                    WHERE id = ?
                """, (balance, datetime.now(), existing["id"]))
            else:
                cursor.execute(
                    "INSERT INTO cash_balance (balance) VALUES (?)",
                    (balance,)
                )
            return True

    # ==================== Portfolio Summary ====================

    def get_portfolio_summary(self) -> PortfolioSummary:
        """포트폴리오 요약 조회"""
        positions = self.get_positions()
        cash = self.get_cash_balance()

        total_invested = sum(p.total_invested for p in positions)
        total_value = sum(p.current_value for p in positions)

        return PortfolioSummary(
            total_invested=total_invested,
            total_value=total_value,
            cash_balance=cash,
            positions=positions,
        )

    # ==================== Trade History CRUD ====================

    def add_trade(self, trade: TradeHistory) -> int:
        """거래 기록 추가"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trade_history (
                    symbol, side, quantity, price, timestamp,
                    market_condition, trigger_reason, emotional_state,
                    pnl, pnl_pct, holding_period, related_trade_id,
                    tags, notes, ai_recommendation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.symbol,
                trade.side,
                trade.quantity,
                trade.price,
                trade.timestamp,
                trade.market_condition,
                trade.trigger_reason,
                trade.emotional_state,
                trade.pnl,
                trade.pnl_pct,
                trade.holding_period,
                trade.related_trade_id,
                json.dumps(trade.tags),
                trade.notes,
                trade.ai_recommendation,
            ))
            return cursor.lastrowid

    def get_trades(
        self,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[TradeHistory]:
        """거래 기록 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM trade_history WHERE 1=1"
            params = []

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)

            if side:
                query += " AND side = ?"
                params.append(side)

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [TradeHistory.from_dict(dict(row)) for row in rows]

    def get_trade_by_id(self, trade_id: int) -> Optional[TradeHistory]:
        """특정 거래 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trade_history WHERE id = ?", (trade_id,))
            row = cursor.fetchone()
            return TradeHistory.from_dict(dict(row)) if row else None

    def update_trade(self, trade_id: int, updates: dict) -> bool:
        """거래 기록 업데이트"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            set_clauses = []
            params = []
            for key, value in updates.items():
                if key == "tags" and isinstance(value, list):
                    value = json.dumps(value)
                set_clauses.append(f"{key} = ?")
                params.append(value)

            params.append(trade_id)
            query = f"UPDATE trade_history SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(query, params)
            return cursor.rowcount > 0

    def get_trade_stats(self) -> dict:
        """거래 통계 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 전체 거래 수
            cursor.execute("SELECT COUNT(*) as total FROM trade_history")
            total = cursor.fetchone()["total"]

            # 매도 거래 중 수익/손실 통계
            cursor.execute("""
                SELECT
                    COUNT(*) as total_sells,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) as total_profit,
                    SUM(CASE WHEN pnl < 0 THEN ABS(pnl) ELSE 0 END) as total_loss,
                    AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                    AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss,
                    MAX(pnl) as best_trade,
                    MIN(pnl) as worst_trade,
                    AVG(holding_period) as avg_holding_period
                FROM trade_history
                WHERE side = 'sell' AND pnl IS NOT NULL
            """)
            row = cursor.fetchone()

            total_sells = row["total_sells"] or 0
            wins = row["wins"] or 0
            losses = row["losses"] or 0
            total_profit = row["total_profit"] or 0
            total_loss = row["total_loss"] or 0

            win_rate = (wins / total_sells * 100) if total_sells > 0 else 0
            profit_factor = (total_profit / total_loss) if total_loss > 0 else 0

            return {
                "total_trades": total,
                "total_closed_trades": total_sells,
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "total_profit": total_profit,
                "total_loss": total_loss,
                "avg_win": row["avg_win"] or 0,
                "avg_loss": row["avg_loss"] or 0,
                "best_trade": row["best_trade"] or 0,
                "worst_trade": row["worst_trade"] or 0,
                "avg_holding_period": row["avg_holding_period"] or 0,
            }

    def get_trades_by_trigger(self) -> dict:
        """매매 이유별 통계"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    trigger_reason,
                    COUNT(*) as count,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
                    AVG(pnl_pct) as avg_pnl_pct
                FROM trade_history
                WHERE side = 'sell' AND pnl IS NOT NULL
                GROUP BY trigger_reason
            """)
            rows = cursor.fetchall()

            return {
                row["trigger_reason"]: {
                    "count": row["count"],
                    "wins": row["wins"],
                    "losses": row["losses"],
                    "win_rate": (row["wins"] / row["count"] * 100) if row["count"] > 0 else 0,
                    "avg_pnl_pct": row["avg_pnl_pct"] or 0,
                }
                for row in rows
            }

    def get_trades_by_emotion(self) -> dict:
        """감정 상태별 통계"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    emotional_state,
                    COUNT(*) as count,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
                    AVG(pnl_pct) as avg_pnl_pct
                FROM trade_history
                WHERE side = 'sell' AND pnl IS NOT NULL
                GROUP BY emotional_state
            """)
            rows = cursor.fetchall()

            return {
                row["emotional_state"]: {
                    "count": row["count"],
                    "wins": row["wins"],
                    "losses": row["losses"],
                    "win_rate": (row["wins"] / row["count"] * 100) if row["count"] > 0 else 0,
                    "avg_pnl_pct": row["avg_pnl_pct"] or 0,
                }
                for row in rows
            }

    # ==================== Watchlist CRUD ====================

    def add_to_watchlist(
        self,
        symbol: str,
        alert_conditions: Optional[dict] = None,
        notes: str = ""
    ) -> bool:
        """관심 목록에 추가"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO watchlist (symbol, alert_conditions, notes)
                    VALUES (?, ?, ?)
                """, (
                    symbol,
                    json.dumps(alert_conditions or {}),
                    notes,
                ))
                return True
            except sqlite3.IntegrityError:
                # 이미 존재하는 경우 업데이트
                cursor.execute("""
                    UPDATE watchlist SET
                        alert_conditions = ?,
                        notes = ?
                    WHERE symbol = ?
                """, (json.dumps(alert_conditions or {}), notes, symbol))
                return True

    def remove_from_watchlist(self, symbol: str) -> bool:
        """관심 목록에서 제거"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))
            return cursor.rowcount > 0

    def get_watchlist(self) -> list[WatchlistItem]:
        """관심 목록 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM watchlist ORDER BY symbol")
            rows = cursor.fetchall()
            return [WatchlistItem.from_dict(dict(row)) for row in rows]

    def is_in_watchlist(self, symbol: str) -> bool:
        """관심 목록 포함 여부 확인"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM watchlist WHERE symbol = ?",
                (symbol,)
            )
            return cursor.fetchone() is not None


if __name__ == "__main__":
    # 테스트
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = DBManager(db_path)

        # 프로필 테스트
        profile = InvestorProfile(
            total_capital=5000000,
            risk_tolerance="moderate",
            preferred_coins=["BTC", "ETH", "XRP"]
        )
        db.save_profile(profile)
        loaded_profile = db.get_profile()
        print(f"Profile saved and loaded: {loaded_profile.total_capital:,}원")

        # 포지션 테스트
        position = Position(
            symbol="BTC/KRW",
            quantity=0.01,
            avg_entry_price=50000000,
            current_price=55000000,
            first_buy_date=datetime.now(),
            last_buy_date=datetime.now()
        )
        db.save_position(position)
        db.set_cash_balance(1000000)

        portfolio = db.get_portfolio_summary()
        print(f"Portfolio: {portfolio.total_value:,.0f}원, PnL: {portfolio.total_pnl_pct:.2f}%")

        # 거래 기록 테스트
        trade = TradeHistory(
            symbol="BTC/KRW",
            side="buy",
            quantity=0.01,
            price=50000000,
            timestamp=datetime.now(),
            trigger_reason="AI추천",
            emotional_state="침착"
        )
        trade_id = db.add_trade(trade)
        print(f"Trade added with ID: {trade_id}")

        # 매도 거래 추가 (통계 테스트용)
        sell_trade = TradeHistory(
            symbol="BTC/KRW",
            side="sell",
            quantity=0.01,
            price=55000000,
            timestamp=datetime.now(),
            trigger_reason="AI추천",
            emotional_state="침착",
            pnl=50000,
            pnl_pct=10.0,
            holding_period=24,
            related_trade_id=trade_id
        )
        db.add_trade(sell_trade)

        stats = db.get_trade_stats()
        print(f"Trade stats: Win rate {stats['win_rate']:.1f}%")

        # 관심 목록 테스트
        db.add_to_watchlist("ETH/KRW", {"rsi_below": 30})
        watchlist = db.get_watchlist()
        print(f"Watchlist: {[w.symbol for w in watchlist]}")

        print("\nAll tests passed!")
