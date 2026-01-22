"""
CryptoBrain V2 - 데이터 모델 정의
초개인화 기능을 위한 핵심 데이터 구조
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json


@dataclass
class InvestorProfile:
    """사용자가 직접 입력하는 투자자 기본 정보"""

    # 기본 정보
    total_capital: int = 1000000              # 총 투자 가능 자금 (KRW)
    monthly_income: int = 0                   # 월 수입 (추가 투자 여력 판단)
    investment_goal: str = "장기자산증식"     # "단기수익" | "장기자산증식" | "용돈벌이"
    investment_horizon: str = "1-6개월"       # "1개월미만" | "1-6개월" | "6개월-1년" | "1년이상"

    # 리스크 성향
    max_loss_tolerance: float = 0.1           # 최대 감내 가능 손실률 (예: 0.1 = 10%)
    risk_per_trade: float = 0.02              # 1회 거래당 리스크 % (기본 2%)
    risk_tolerance: str = "moderate"          # "aggressive" | "moderate" | "conservative"
    preferred_volatility: str = "medium"      # "low" | "medium" | "high"
    leverage_allowed: bool = False            # 레버리지 사용 여부

    # 거래 스타일
    trading_style: str = "swing"              # "scalping" | "swing" | "position"
    trading_frequency: str = "weekly"         # "daily" | "weekly" | "monthly"
    preferred_session: str = "asia"           # "asia" | "europe" | "us" | "all"
    available_time_per_day: int = 30          # 차트 볼 수 있는 시간 (분)
    active_hours_start: str = "09:00"         # 활성 시간 시작
    active_hours_end: str = "23:00"           # 활성 시간 종료

    # 경험 수준
    experience_years: float = 1.0             # 투자 경력 (년)
    technical_analysis_skill: str = "beginner"  # "beginner" | "intermediate" | "advanced"
    past_major_mistakes: list = field(default_factory=list)  # ["FOMO매수", "손절못함", "물타기"] 등

    # 선호 코인
    preferred_coins: list = field(default_factory=lambda: ["BTC", "ETH"])

    # 메타데이터
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "total_capital": self.total_capital,
            "monthly_income": self.monthly_income,
            "investment_goal": self.investment_goal,
            "investment_horizon": self.investment_horizon,
            "max_loss_tolerance": self.max_loss_tolerance,
            "risk_per_trade": self.risk_per_trade,
            "risk_tolerance": self.risk_tolerance,
            "preferred_volatility": self.preferred_volatility,
            "leverage_allowed": self.leverage_allowed,
            "trading_style": self.trading_style,
            "trading_frequency": self.trading_frequency,
            "preferred_session": self.preferred_session,
            "available_time_per_day": self.available_time_per_day,
            "active_hours_start": self.active_hours_start,
            "active_hours_end": self.active_hours_end,
            "experience_years": self.experience_years,
            "technical_analysis_skill": self.technical_analysis_skill,
            "past_major_mistakes": self.past_major_mistakes,
            "preferred_coins": self.preferred_coins,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InvestorProfile":
        """딕셔너리에서 생성"""
        # JSON 문자열 필드 처리
        if isinstance(data.get("past_major_mistakes"), str):
            data["past_major_mistakes"] = json.loads(data["past_major_mistakes"])
        if isinstance(data.get("preferred_coins"), str):
            data["preferred_coins"] = json.loads(data["preferred_coins"])

        return cls(
            total_capital=data.get("total_capital", 1000000),
            monthly_income=data.get("monthly_income", 0),
            investment_goal=data.get("investment_goal", "장기자산증식"),
            investment_horizon=data.get("investment_horizon", "1-6개월"),
            max_loss_tolerance=data.get("max_loss_tolerance", 0.1),
            risk_per_trade=data.get("risk_per_trade", 0.02),
            risk_tolerance=data.get("risk_tolerance", "moderate"),
            preferred_volatility=data.get("preferred_volatility", "medium"),
            leverage_allowed=data.get("leverage_allowed", False),
            trading_style=data.get("trading_style", "swing"),
            trading_frequency=data.get("trading_frequency", "weekly"),
            preferred_session=data.get("preferred_session", "asia"),
            available_time_per_day=data.get("available_time_per_day", 30),
            active_hours_start=data.get("active_hours_start", "09:00"),
            active_hours_end=data.get("active_hours_end", "23:00"),
            experience_years=data.get("experience_years", 1.0),
            technical_analysis_skill=data.get("technical_analysis_skill", "beginner"),
            past_major_mistakes=data.get("past_major_mistakes", []),
            preferred_coins=data.get("preferred_coins", ["BTC", "ETH"]),
            id=data.get("id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class Position:
    """개별 포지션 (보유 종목)"""

    symbol: str                               # "BTC/KRW"
    quantity: float = 0.0                     # 보유 수량
    avg_entry_price: float = 0.0              # 평균 매수가
    current_price: float = 0.0                # 현재가 (자동 업데이트)
    first_buy_date: Optional[datetime] = None # 최초 매수일
    last_buy_date: Optional[datetime] = None  # 최근 매수일

    # 메타데이터
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def total_invested(self) -> float:
        """총 투자금"""
        return self.quantity * self.avg_entry_price

    @property
    def current_value(self) -> float:
        """현재 평가금"""
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        """미실현 손익"""
        return self.current_value - self.total_invested

    @property
    def unrealized_pnl_pct(self) -> float:
        """미실현 손익률"""
        if self.total_invested == 0:
            return 0.0
        return (self.unrealized_pnl / self.total_invested) * 100

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "avg_entry_price": self.avg_entry_price,
            "current_price": self.current_price,
            "first_buy_date": self.first_buy_date.isoformat() if self.first_buy_date else None,
            "last_buy_date": self.last_buy_date.isoformat() if self.last_buy_date else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Position":
        """딕셔너리에서 생성"""
        first_buy = data.get("first_buy_date")
        last_buy = data.get("last_buy_date")

        return cls(
            symbol=data.get("symbol", ""),
            quantity=data.get("quantity", 0.0),
            avg_entry_price=data.get("avg_entry_price", 0.0),
            current_price=data.get("current_price", 0.0),
            first_buy_date=datetime.fromisoformat(first_buy) if isinstance(first_buy, str) else first_buy,
            last_buy_date=datetime.fromisoformat(last_buy) if isinstance(last_buy, str) else last_buy,
            id=data.get("id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class PortfolioSummary:
    """포트폴리오 요약 정보"""

    total_invested: float = 0.0               # 총 투자금
    total_value: float = 0.0                  # 현재 평가금
    cash_balance: float = 0.0                 # 현금 (KRW)
    positions: list = field(default_factory=list)  # Position 리스트

    @property
    def total_pnl(self) -> float:
        """총 손익"""
        return self.total_value - self.total_invested

    @property
    def total_pnl_pct(self) -> float:
        """총 수익률"""
        if self.total_invested == 0:
            return 0.0
        return (self.total_pnl / self.total_invested) * 100

    @property
    def allocation(self) -> dict:
        """비중 분석"""
        total = self.total_value + self.cash_balance
        if total == 0:
            return {"현금": 1.0}

        alloc = {}
        for pos in self.positions:
            if pos.current_value > 0:
                coin = pos.symbol.split("/")[0]
                alloc[coin] = pos.current_value / total

        alloc["현금"] = self.cash_balance / total if total > 0 else 0
        return alloc

    @property
    def largest_position(self) -> str:
        """가장 큰 비중 코인"""
        alloc = self.allocation
        if not alloc or alloc.get("현금", 0) == 1.0:
            return "없음"

        # 현금 제외하고 가장 큰 비중 찾기
        non_cash = {k: v for k, v in alloc.items() if k != "현금"}
        if not non_cash:
            return "없음"
        return max(non_cash, key=non_cash.get)

    @property
    def concentration_risk(self) -> str:
        """집중 리스크 평가"""
        alloc = self.allocation
        max_alloc = max(v for k, v in alloc.items() if k != "현금") if len(alloc) > 1 else 0

        if max_alloc >= 0.5:
            return "high"
        elif max_alloc >= 0.3:
            return "medium"
        return "low"


@dataclass
class TradeHistory:
    """매매 이력 - AI 학습의 핵심 데이터"""

    symbol: str                               # "BTC/KRW"
    side: str                                 # "buy" | "sell"
    quantity: float = 0.0                     # 거래 수량
    price: float = 0.0                        # 거래 가격
    timestamp: Optional[datetime] = None      # 거래 시간

    # 매매 맥락 (AI 학습용)
    market_condition: str = "sideways"        # "bull" | "bear" | "sideways"
    trigger_reason: str = "본인판단"          # "AI추천" | "본인판단" | "뉴스" | "FOMO" | "공포매도"
    emotional_state: str = "침착"             # "침착" | "흥분" | "불안" | "확신"

    # 결과 (청산 시)
    pnl: Optional[float] = None               # 손익 금액
    pnl_pct: Optional[float] = None           # 손익 %
    holding_period: Optional[int] = None      # 보유 기간 (시간)

    # 연결된 거래 (매수-매도 페어링)
    related_trade_id: Optional[int] = None    # 연결된 거래 ID

    # AI 분석용 태그
    tags: list = field(default_factory=list)  # ["손절성공", "목표가도달", "조기청산", "물타기"]

    # 메모
    notes: str = ""
    ai_recommendation: str = ""               # 당시 AI 추천 내용

    # 메타데이터
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "market_condition": self.market_condition,
            "trigger_reason": self.trigger_reason,
            "emotional_state": self.emotional_state,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "holding_period": self.holding_period,
            "related_trade_id": self.related_trade_id,
            "tags": self.tags,
            "notes": self.notes,
            "ai_recommendation": self.ai_recommendation,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TradeHistory":
        """딕셔너리에서 생성"""
        timestamp = data.get("timestamp")
        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = json.loads(tags)

        return cls(
            symbol=data.get("symbol", ""),
            side=data.get("side", "buy"),
            quantity=data.get("quantity", 0.0),
            price=data.get("price", 0.0),
            timestamp=datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp,
            market_condition=data.get("market_condition", "sideways"),
            trigger_reason=data.get("trigger_reason", "본인판단"),
            emotional_state=data.get("emotional_state", "침착"),
            pnl=data.get("pnl"),
            pnl_pct=data.get("pnl_pct"),
            holding_period=data.get("holding_period"),
            related_trade_id=data.get("related_trade_id"),
            tags=tags,
            notes=data.get("notes", ""),
            ai_recommendation=data.get("ai_recommendation", ""),
            id=data.get("id"),
            created_at=data.get("created_at"),
        )


@dataclass
class WatchlistItem:
    """관심 코인"""

    symbol: str                               # "BTC/KRW"
    alert_conditions: dict = field(default_factory=dict)  # {"rsi_below": 30, "price_above": 100000}
    notes: str = ""

    # 메타데이터
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "symbol": self.symbol,
            "alert_conditions": self.alert_conditions,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WatchlistItem":
        """딕셔너리에서 생성"""
        conditions = data.get("alert_conditions", {})
        if isinstance(conditions, str):
            conditions = json.loads(conditions)

        return cls(
            symbol=data.get("symbol", ""),
            alert_conditions=conditions,
            notes=data.get("notes", ""),
            id=data.get("id"),
            created_at=data.get("created_at"),
        )


# 상수 정의
INVESTMENT_GOALS = ["단기수익", "장기자산증식", "용돈벌이"]
INVESTMENT_HORIZONS = ["1개월미만", "1-6개월", "6개월-1년", "1년이상"]
RISK_TOLERANCES = ["aggressive", "moderate", "conservative"]
VOLATILITY_PREFERENCES = ["low", "medium", "high"]
TRADING_STYLES = ["scalping", "swing", "position"]
TRADING_FREQUENCIES = ["daily", "weekly", "monthly"]
TRADING_SESSIONS = ["asia", "europe", "us", "all"]
SKILL_LEVELS = ["beginner", "intermediate", "advanced"]
MARKET_CONDITIONS = ["bull", "bear", "sideways"]
TRIGGER_REASONS = ["AI추천", "본인판단", "뉴스", "FOMO", "공포매도"]
EMOTIONAL_STATES = ["침착", "흥분", "불안", "확신"]
COMMON_MISTAKES = ["FOMO매수", "손절못함", "물타기", "조기익절", "과도한거래", "레버리지남용"]
TRADE_TAGS = ["손절성공", "목표가도달", "조기청산", "물타기", "FOMO", "패닉셀"]


if __name__ == "__main__":
    # 테스트
    profile = InvestorProfile(
        total_capital=5000000,
        risk_tolerance="moderate",
        preferred_coins=["BTC", "ETH", "XRP"]
    )
    print("Profile:", profile.to_dict())

    position = Position(
        symbol="BTC/KRW",
        quantity=0.01,
        avg_entry_price=50000000,
        current_price=55000000
    )
    print(f"Position PnL: {position.unrealized_pnl:,.0f}원 ({position.unrealized_pnl_pct:.2f}%)")

    trade = TradeHistory(
        symbol="BTC/KRW",
        side="buy",
        quantity=0.01,
        price=50000000,
        timestamp=datetime.now(),
        trigger_reason="AI추천",
        emotional_state="침착"
    )
    print("Trade:", trade.to_dict())
