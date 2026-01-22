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

            # 임포트된 거래 테이블 (CSV 데이터)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS imported_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    exchange TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    market TEXT DEFAULT 'KRW',
                    trade_type TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    total_amount REAL NOT NULL,
                    fee REAL DEFAULT 0,
                    timestamp TIMESTAMP NOT NULL,
                    order_id TEXT,
                    realized_pnl REAL,
                    avg_buy_price REAL,
                    import_batch_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 임포트 배치 테이블 (임포트 이력)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS import_batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT NOT NULL UNIQUE,
                    exchange TEXT NOT NULL,
                    file_name TEXT,
                    total_rows INTEGER DEFAULT 0,
                    parsed_rows INTEGER DEFAULT 0,
                    skipped_rows INTEGER DEFAULT 0,
                    total_buy_amount REAL DEFAULT 0,
                    total_sell_amount REAL DEFAULT 0,
                    total_fee REAL DEFAULT 0,
                    date_range_start TIMESTAMP,
                    date_range_end TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 인덱스 생성
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_imported_trades_symbol
                ON imported_trades(symbol)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_imported_trades_timestamp
                ON imported_trades(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_imported_trades_batch
                ON imported_trades(import_batch_id)
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

    # ==================== Imported Trades CRUD ====================

    def save_imported_trades(
        self,
        trades: list,
        exchange: str,
        file_name: str = "",
        batch_id: Optional[str] = None
    ) -> dict:
        """
        임포트된 거래 데이터 저장

        Args:
            trades: ParsedTrade 객체 리스트
            exchange: 거래소명
            file_name: 원본 파일명
            batch_id: 배치 ID (없으면 자동 생성)

        Returns:
            dict: 저장 결과 {batch_id, saved_count}
        """
        import uuid

        if not batch_id:
            batch_id = str(uuid.uuid4())[:8]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            saved_count = 0

            # 거래 데이터 저장
            for trade in trades:
                try:
                    # trade가 dict인지 객체인지 확인
                    if hasattr(trade, 'to_dict'):
                        data = trade.to_dict()
                    else:
                        data = trade

                    cursor.execute("""
                        INSERT INTO imported_trades (
                            exchange, symbol, market, trade_type,
                            quantity, price, total_amount, fee,
                            timestamp, order_id, realized_pnl, avg_buy_price,
                            import_batch_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        exchange,
                        data.get("symbol", ""),
                        data.get("market", "KRW"),
                        data.get("trade_type", ""),
                        data.get("quantity", 0),
                        data.get("price", 0),
                        data.get("total_amount", 0),
                        data.get("fee", 0),
                        data.get("timestamp"),
                        data.get("order_id"),
                        data.get("realized_pnl"),
                        data.get("avg_buy_price"),
                        batch_id,
                    ))
                    saved_count += 1
                except Exception as e:
                    print(f"Trade save error: {e}")
                    continue

            # 배치 정보 저장
            total_buy = sum(
                t.total_amount if hasattr(t, 'total_amount') else t.get("total_amount", 0)
                for t in trades
                if (t.trade_type.value if hasattr(t, 'trade_type') and hasattr(t.trade_type, 'value')
                    else t.get("trade_type", "")) == "buy"
            )
            total_sell = sum(
                t.total_amount if hasattr(t, 'total_amount') else t.get("total_amount", 0)
                for t in trades
                if (t.trade_type.value if hasattr(t, 'trade_type') and hasattr(t.trade_type, 'value')
                    else t.get("trade_type", "")) == "sell"
            )
            total_fee = sum(
                t.fee if hasattr(t, 'fee') else t.get("fee", 0)
                for t in trades
            )

            # 날짜 범위 계산
            timestamps = []
            for t in trades:
                ts = t.timestamp if hasattr(t, 'timestamp') else t.get("timestamp")
                if ts:
                    timestamps.append(ts)

            date_start = min(timestamps) if timestamps else None
            date_end = max(timestamps) if timestamps else None

            cursor.execute("""
                INSERT INTO import_batches (
                    batch_id, exchange, file_name,
                    total_rows, parsed_rows, skipped_rows,
                    total_buy_amount, total_sell_amount, total_fee,
                    date_range_start, date_range_end
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                batch_id,
                exchange,
                file_name,
                len(trades),
                saved_count,
                len(trades) - saved_count,
                total_buy,
                total_sell,
                total_fee,
                date_start,
                date_end,
            ))

            return {"batch_id": batch_id, "saved_count": saved_count}

    def get_imported_trades(
        self,
        symbol: Optional[str] = None,
        exchange: Optional[str] = None,
        trade_type: Optional[str] = None,
        batch_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict]:
        """
        임포트된 거래 조회

        Args:
            symbol: 필터링할 심볼
            exchange: 거래소 필터
            trade_type: 'buy' 또는 'sell'
            batch_id: 배치 ID 필터
            start_date: 시작일
            end_date: 종료일
            limit: 최대 결과 수
            offset: 시작 위치

        Returns:
            list[dict]: 거래 목록
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM imported_trades WHERE 1=1"
            params = []

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)

            if exchange:
                query += " AND exchange = ?"
                params.append(exchange)

            if trade_type:
                query += " AND trade_type = ?"
                params.append(trade_type)

            if batch_id:
                query += " AND import_batch_id = ?"
                params.append(batch_id)

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat() if isinstance(start_date, datetime) else start_date)

            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat() if isinstance(end_date, datetime) else end_date)

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def get_import_batches(self, limit: int = 20) -> list[dict]:
        """임포트 배치 이력 조회"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM import_batches
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def delete_import_batch(self, batch_id: str) -> bool:
        """임포트 배치 삭제 (해당 거래 데이터도 함께 삭제)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 거래 데이터 삭제
            cursor.execute(
                "DELETE FROM imported_trades WHERE import_batch_id = ?",
                (batch_id,)
            )
            deleted_trades = cursor.rowcount

            # 배치 정보 삭제
            cursor.execute(
                "DELETE FROM import_batches WHERE batch_id = ?",
                (batch_id,)
            )

            return deleted_trades > 0

    def get_imported_trade_stats(
        self,
        symbol: Optional[str] = None,
        exchange: Optional[str] = None
    ) -> dict:
        """
        임포트된 거래 통계

        Args:
            symbol: 특정 심볼 필터
            exchange: 거래소 필터

        Returns:
            dict: 통계 데이터
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            where_clause = "WHERE 1=1"
            params = []

            if symbol:
                where_clause += " AND symbol = ?"
                params.append(symbol)

            if exchange:
                where_clause += " AND exchange = ?"
                params.append(exchange)

            # 기본 통계
            cursor.execute(f"""
                SELECT
                    COUNT(*) as total_trades,
                    COUNT(DISTINCT symbol) as unique_symbols,
                    SUM(CASE WHEN trade_type = 'buy' THEN total_amount ELSE 0 END) as total_buy_amount,
                    SUM(CASE WHEN trade_type = 'sell' THEN total_amount ELSE 0 END) as total_sell_amount,
                    SUM(fee) as total_fee,
                    SUM(CASE WHEN trade_type = 'sell' AND realized_pnl IS NOT NULL THEN realized_pnl ELSE 0 END) as total_realized_pnl,
                    MIN(timestamp) as first_trade_date,
                    MAX(timestamp) as last_trade_date
                FROM imported_trades
                {where_clause}
            """, params)
            row = cursor.fetchone()

            # 수익/손실 거래 수
            cursor.execute(f"""
                SELECT
                    COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) as win_count,
                    COUNT(CASE WHEN realized_pnl < 0 THEN 1 END) as loss_count,
                    AVG(CASE WHEN realized_pnl > 0 THEN realized_pnl END) as avg_win,
                    AVG(CASE WHEN realized_pnl < 0 THEN realized_pnl END) as avg_loss
                FROM imported_trades
                {where_clause} AND trade_type = 'sell' AND realized_pnl IS NOT NULL
            """, params)
            pnl_row = cursor.fetchone()

            win_count = pnl_row["win_count"] or 0
            loss_count = pnl_row["loss_count"] or 0
            total_closed = win_count + loss_count

            return {
                "total_trades": row["total_trades"] or 0,
                "unique_symbols": row["unique_symbols"] or 0,
                "total_buy_amount": row["total_buy_amount"] or 0,
                "total_sell_amount": row["total_sell_amount"] or 0,
                "total_fee": row["total_fee"] or 0,
                "total_realized_pnl": row["total_realized_pnl"] or 0,
                "first_trade_date": row["first_trade_date"],
                "last_trade_date": row["last_trade_date"],
                "win_count": win_count,
                "loss_count": loss_count,
                "win_rate": (win_count / total_closed * 100) if total_closed > 0 else 0,
                "avg_win": pnl_row["avg_win"] or 0,
                "avg_loss": pnl_row["avg_loss"] or 0,
            }

    def get_symbol_summary_from_imports(self) -> list[dict]:
        """임포트 데이터 기반 종목별 요약"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    symbol,
                    SUM(CASE WHEN trade_type = 'buy' THEN quantity ELSE 0 END) as total_bought,
                    SUM(CASE WHEN trade_type = 'sell' THEN quantity ELSE 0 END) as total_sold,
                    SUM(CASE WHEN trade_type = 'buy' THEN total_amount ELSE 0 END) as total_buy_amount,
                    SUM(CASE WHEN trade_type = 'sell' THEN total_amount ELSE 0 END) as total_sell_amount,
                    SUM(CASE WHEN trade_type = 'sell' THEN realized_pnl ELSE 0 END) as total_pnl,
                    COUNT(*) as trade_count,
                    MAX(timestamp) as last_trade_date
                FROM imported_trades
                GROUP BY symbol
                ORDER BY total_buy_amount DESC
            """)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                data = dict(row)
                data["current_quantity"] = (data["total_bought"] or 0) - (data["total_sold"] or 0)
                if data["total_bought"] and data["total_bought"] > 0:
                    data["avg_buy_price"] = (data["total_buy_amount"] or 0) / data["total_bought"]
                else:
                    data["avg_buy_price"] = 0
                results.append(data)

            return results


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
