"""
CryptoBrain V3 - 기대값(Expected Value) 계산기

핵심 철학: EV > 0인 거래만 실행
EV = (승률 × 평균수익) - (패률 × 평균손실)
"""
from dataclasses import dataclass, field
from typing import Optional, Tuple
from enum import Enum
import numpy as np


class Recommendation(Enum):
    """거래 추천 유형"""
    ENTER = "enter"      # 진입 추천
    SKIP = "skip"        # 진입 금지
    WAIT = "wait"        # 조건 대기


class Confidence(Enum):
    """신뢰도 수준"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TradeSetup:
    """거래 셋업 정의"""
    symbol: str
    side: str                      # "long" | "short"
    entry_price: float
    stop_loss: float
    take_profit: float

    # 계산된 값 (자동 설정)
    risk_percent: float = 0.0      # 손절 시 손실률
    reward_percent: float = 0.0    # 익절 시 수익률
    risk_reward_ratio: float = 0.0 # 손익비

    def calculate_risk_reward(self):
        """손익비 계산"""
        if self.entry_price <= 0:
            return

        if self.side == "long":
            self.risk_percent = abs(self.entry_price - self.stop_loss) / self.entry_price * 100
            self.reward_percent = abs(self.take_profit - self.entry_price) / self.entry_price * 100
        else:  # short
            self.risk_percent = abs(self.stop_loss - self.entry_price) / self.entry_price * 100
            self.reward_percent = abs(self.entry_price - self.take_profit) / self.entry_price * 100

        if self.risk_percent > 0:
            self.risk_reward_ratio = self.reward_percent / self.risk_percent
        else:
            self.risk_reward_ratio = 0


@dataclass
class EVAnalysis:
    """기대값 분석 결과"""
    expected_value: float           # 기대값 (%)
    win_probability: float          # 예상 승률 (0~1)
    risk_reward_ratio: float        # 손익비
    kelly_fraction: float           # 켈리 기준 베팅 비율

    recommendation: Recommendation  # ENTER | SKIP | WAIT
    confidence: Confidence          # HIGH | MEDIUM | LOW
    reasoning: list = field(default_factory=list)  # 판단 근거

    # 추가 정보
    risk_percent: float = 0.0
    reward_percent: float = 0.0
    optimal_position_pct: float = 0.0  # 최적 포지션 크기 (%)

    def to_dict(self) -> dict:
        return {
            "expected_value": self.expected_value,
            "win_probability": self.win_probability,
            "risk_reward_ratio": self.risk_reward_ratio,
            "kelly_fraction": self.kelly_fraction,
            "recommendation": self.recommendation.value,
            "confidence": self.confidence.value,
            "reasoning": self.reasoning,
            "risk_percent": self.risk_percent,
            "reward_percent": self.reward_percent,
            "optimal_position_pct": self.optimal_position_pct,
        }


class ExpectedValueCalculator:
    """
    모든 거래의 기대값을 계산하여 수익성 판단

    핵심 공식:
    EV = (Win% × Avg_Win) - (Loss% × Avg_Loss)

    EV > 0 이어야만 거래 가치가 있음

    켈리 기준:
    Kelly% = W - [(1-W) / R]
    W = 승률, R = 손익비
    """

    # 최소 기준값
    MIN_RISK_REWARD = 1.5      # 최소 손익비
    MIN_WIN_PROB = 0.35        # 최소 승률
    MIN_EV = 0.5               # 최소 기대값 (%)
    MAX_KELLY = 0.25           # 최대 켈리 비율 (25%)

    def __init__(self, historical_data: dict = None):
        """
        Args:
            historical_data: 과거 유사 패턴의 성과 데이터
        """
        self.historical = historical_data or {}

        # 기본 패턴별 승률 (과거 데이터 없을 때 사용)
        self.default_pattern_probs = {
            "rsi_oversold": 0.58,       # RSI 과매도 매수
            "rsi_overbought": 0.55,     # RSI 과매수 매도
            "trend_following": 0.52,     # 추세 추종
            "counter_trend": 0.42,       # 역추세
            "breakout": 0.48,            # 돌파 매매
            "support_bounce": 0.55,      # 지지선 반등
            "resistance_rejection": 0.53, # 저항선 거부
            "default": 0.50              # 기본값
        }

    def analyze(self, setup: TradeSetup, market_context: dict = None) -> EVAnalysis:
        """
        거래 셋업의 기대값 분석

        Args:
            setup: 거래 셋업 정보
            market_context: 시장 맥락 (MarketAnalyzer 결과)

        Returns:
            EVAnalysis: 기대값 분석 결과
        """
        context = market_context or {}

        # 1. 손익비 계산
        setup.calculate_risk_reward()

        # 2. 승률 추정 (여러 요소 종합)
        win_probability = self._estimate_win_probability(setup, context)

        # 3. 기대값 계산
        # EV = (승률 × 수익률) - (패률 × 손실률)
        expected_value = (
            (win_probability * setup.reward_percent) -
            ((1 - win_probability) * setup.risk_percent)
        )

        # 4. 켈리 기준 계산
        kelly = self._calculate_kelly(win_probability, setup.risk_reward_ratio)

        # 5. 최종 판단
        recommendation, confidence, reasoning = self._make_decision(
            expected_value, win_probability, setup.risk_reward_ratio, context
        )

        # 6. 최적 포지션 크기 계산
        # Half Kelly 적용하고 최대 5%로 제한
        optimal_position = min(kelly * 100, 5.0)

        return EVAnalysis(
            expected_value=round(expected_value, 2),
            win_probability=round(win_probability, 3),
            risk_reward_ratio=round(setup.risk_reward_ratio, 2),
            kelly_fraction=round(kelly, 4),
            recommendation=recommendation,
            confidence=confidence,
            reasoning=reasoning,
            risk_percent=round(setup.risk_percent, 2),
            reward_percent=round(setup.reward_percent, 2),
            optimal_position_pct=round(optimal_position, 2),
        )

    def _estimate_win_probability(self, setup: TradeSetup, context: dict) -> float:
        """
        승률 추정 (여러 요소 종합)

        고려 요소:
        1. 과거 유사 패턴 승률
        2. 현재 기술적 지표 상태
        3. 시장 추세와의 정렬
        4. 손익비 (높을수록 승률 하향 조정)
        """
        scores = []
        weights = []

        # 1. 과거 유사 패턴 승률 (가중치: 30%)
        pattern_prob = self._get_pattern_probability(setup, context)
        scores.append(pattern_prob)
        weights.append(0.30)

        # 2. 기술적 지표 점수 (가중치: 30%)
        technical_score = self._calculate_technical_score(setup, context)
        scores.append(technical_score)
        weights.append(0.30)

        # 3. 추세 정렬 점수 (가중치: 25%)
        trend_alignment = self._calculate_trend_alignment(setup, context)
        scores.append(trend_alignment)
        weights.append(0.25)

        # 4. 손익비 조정 (가중치: 15%)
        # 높은 손익비는 달성 확률이 낮음
        rr_adjustment = self._adjust_for_risk_reward(setup.risk_reward_ratio)
        scores.append(rr_adjustment)
        weights.append(0.15)

        # 가중 평균 계산
        final_probability = sum(s * w for s, w in zip(scores, weights))

        # 0.2 ~ 0.8 범위로 클램핑 (과신/과소평가 방지)
        return max(0.20, min(0.80, final_probability))

    def _get_pattern_probability(self, setup: TradeSetup, context: dict) -> float:
        """패턴 기반 승률 추정"""

        # RSI 기반 패턴 확인
        rsi = context.get("rsi", 50)

        if setup.side == "long":
            if rsi < 30:
                return self.default_pattern_probs["rsi_oversold"]
            elif context.get("ma_alignment") == "bullish":
                return self.default_pattern_probs["trend_following"]
            elif context.get("trend_direction") == "down":
                return self.default_pattern_probs["counter_trend"]
        else:  # short
            if rsi > 70:
                return self.default_pattern_probs["rsi_overbought"]
            elif context.get("ma_alignment") == "bearish":
                return self.default_pattern_probs["trend_following"]
            elif context.get("trend_direction") == "up":
                return self.default_pattern_probs["counter_trend"]

        # 지지/저항 기반
        distance_to_support = context.get("distance_to_support_pct", 100)
        distance_to_resistance = context.get("distance_to_resistance_pct", 100)

        if setup.side == "long" and distance_to_support < 2:
            return self.default_pattern_probs["support_bounce"]
        if setup.side == "short" and distance_to_resistance < 2:
            return self.default_pattern_probs["resistance_rejection"]

        return self.default_pattern_probs["default"]

    def _calculate_technical_score(self, setup: TradeSetup, context: dict) -> float:
        """기술적 지표 기반 점수"""
        score = 0.5  # 기본값

        rsi = context.get("rsi", 50)
        macd_signal = context.get("macd_signal", "neutral")
        ma_alignment = context.get("ma_alignment", "neutral")

        if setup.side == "long":
            # RSI 점수 (과매도일수록 높음)
            if rsi < 30:
                score += 0.15
            elif rsi < 40:
                score += 0.10
            elif rsi > 70:
                score -= 0.15
            elif rsi > 60:
                score -= 0.08

            # MACD 점수
            if macd_signal == "bullish":
                score += 0.10
            elif macd_signal == "bearish":
                score -= 0.10

            # MA 정렬 점수
            if ma_alignment == "bullish":
                score += 0.08
            elif ma_alignment == "bearish":
                score -= 0.08

        else:  # short
            # RSI 점수 (과매수일수록 높음)
            if rsi > 70:
                score += 0.15
            elif rsi > 60:
                score += 0.10
            elif rsi < 30:
                score -= 0.15
            elif rsi < 40:
                score -= 0.08

            # MACD 점수
            if macd_signal == "bearish":
                score += 0.10
            elif macd_signal == "bullish":
                score -= 0.10

            # MA 정렬 점수
            if ma_alignment == "bearish":
                score += 0.08
            elif ma_alignment == "bullish":
                score -= 0.08

        return max(0.2, min(0.8, score))

    def _calculate_trend_alignment(self, setup: TradeSetup, context: dict) -> float:
        """추세 정렬 점수"""
        trend_direction = context.get("trend_direction", "sideways")
        trend_strength = context.get("trend_strength", "weak")

        # 기본 점수
        score = 0.5

        # 추세 방향과의 정렬
        if setup.side == "long":
            if trend_direction == "up":
                score += 0.2
            elif trend_direction == "down":
                score -= 0.15
        else:  # short
            if trend_direction == "down":
                score += 0.2
            elif trend_direction == "up":
                score -= 0.15

        # 추세 강도 반영
        strength_value = context.get("trend_strength_value", "moderate")
        if isinstance(strength_value, str):
            if strength_value == "strong":
                # 강한 추세면 정렬 여부에 따라 더 큰 영향
                if (setup.side == "long" and trend_direction == "up") or \
                   (setup.side == "short" and trend_direction == "down"):
                    score += 0.1
                else:
                    score -= 0.1
            elif strength_value == "weak":
                # 약한 추세면 영향 감소
                score = 0.5 + (score - 0.5) * 0.5

        return max(0.2, min(0.8, score))

    def _adjust_for_risk_reward(self, rr_ratio: float) -> float:
        """
        손익비에 따른 승률 조정

        손익비가 높을수록 목표가 도달 확률은 낮아짐
        1:1 → ~0.55
        1:2 → ~0.50
        1:3 → ~0.45
        1:4+ → ~0.40
        """
        if rr_ratio <= 1.0:
            return 0.55
        elif rr_ratio <= 1.5:
            return 0.52
        elif rr_ratio <= 2.0:
            return 0.50
        elif rr_ratio <= 2.5:
            return 0.47
        elif rr_ratio <= 3.0:
            return 0.45
        else:
            return 0.40

    def _calculate_kelly(self, win_prob: float, rr_ratio: float) -> float:
        """
        켈리 기준 계산

        Kelly% = W - [(1-W) / R]
        W = 승률
        R = 손익비

        결과: 자본의 몇 %를 베팅해야 하는가
        """
        if rr_ratio <= 0:
            return 0

        kelly = win_prob - ((1 - win_prob) / rr_ratio)

        # Half Kelly 적용 (보수적 접근)
        half_kelly = kelly / 2

        # 0 ~ MAX_KELLY 범위로 제한
        return max(0, min(self.MAX_KELLY, half_kelly))

    def _make_decision(
        self,
        ev: float,
        win_prob: float,
        rr_ratio: float,
        context: dict
    ) -> Tuple[Recommendation, Confidence, list]:
        """
        최종 의사결정

        ENTER: 모든 조건 충족
        SKIP: 기대값 음수 또는 심각한 문제
        WAIT: 일부 조건 미충족, 개선 가능성
        """
        reasoning = []

        # === 기대값 체크 ===
        if ev < 0:
            reasoning.append(f"❌ 기대값 {ev:+.2f}%로 마이너스 (손실 예상)")
            reasoning.append("   → 이 거래는 수학적으로 불리합니다")
            return Recommendation.SKIP, Confidence.HIGH, reasoning

        if ev < self.MIN_EV:
            reasoning.append(f"⚠️ 기대값 {ev:+.2f}%로 너무 낮음 (최소 {self.MIN_EV}% 필요)")
            reasoning.append("   → 수수료와 슬리피지 고려 시 손실 가능")
            return Recommendation.SKIP, Confidence.MEDIUM, reasoning

        # === 손익비 체크 ===
        if rr_ratio < 1.0:
            reasoning.append(f"❌ 손익비 1:{rr_ratio:.1f}로 손실이 수익보다 큼")
            reasoning.append("   → 손절가를 좁히거나 목표가를 높이세요")
            return Recommendation.SKIP, Confidence.HIGH, reasoning

        if rr_ratio < self.MIN_RISK_REWARD:
            reasoning.append(f"⚠️ 손익비 1:{rr_ratio:.1f}로 불리함 (최소 1:{self.MIN_RISK_REWARD} 권장)")
            reasoning.append("   → 더 좋은 진입점을 기다리거나 목표가 조정 필요")
            return Recommendation.WAIT, Confidence.MEDIUM, reasoning

        # === 승률 체크 ===
        if win_prob < self.MIN_WIN_PROB:
            reasoning.append(f"⚠️ 추정 승률 {win_prob*100:.0f}%로 낮음 (최소 {self.MIN_WIN_PROB*100:.0f}% 필요)")
            reasoning.append("   → 기술적 조건이 더 유리해질 때 재검토")
            return Recommendation.WAIT, Confidence.LOW, reasoning

        # === 변동성 체크 ===
        volatility = context.get("volatility_regime", "normal")
        if volatility == "extreme":
            reasoning.append("⚠️ 극심한 변동성 - 포지션 크기 50% 축소 권장")

        # === 모든 조건 충족 ===
        reasoning.append(f"✅ 기대값 +{ev:.2f}% (양수)")
        reasoning.append(f"✅ 손익비 1:{rr_ratio:.1f} (유리)")
        reasoning.append(f"✅ 추정 승률 {win_prob*100:.0f}%")

        # 신뢰도 판단
        if ev > 2.0 and rr_ratio >= 2.0 and win_prob >= 0.55:
            confidence = Confidence.HIGH
            reasoning.append("📊 신뢰도: 높음 - 우수한 기회")
        elif ev > 1.0 and rr_ratio >= 1.5 and win_prob >= 0.45:
            confidence = Confidence.MEDIUM
            reasoning.append("📊 신뢰도: 보통 - 양호한 기회")
        else:
            confidence = Confidence.LOW
            reasoning.append("📊 신뢰도: 낮음 - 소규모 포지션 권장")

        return Recommendation.ENTER, confidence, reasoning

    def quick_evaluate(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        side: str = "long",
        symbol: str = "BTC"
    ) -> dict:
        """
        빠른 기대값 평가 (간단한 입력으로)

        Returns:
            dict: {"ev": float, "rr": float, "verdict": str}
        """
        setup = TradeSetup(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit
        )

        analysis = self.analyze(setup)

        verdict_map = {
            Recommendation.ENTER: "✅ 진입 가능",
            Recommendation.SKIP: "❌ 진입 금지",
            Recommendation.WAIT: "⏸️ 조건 대기",
        }

        return {
            "ev": analysis.expected_value,
            "rr": analysis.risk_reward_ratio,
            "win_prob": analysis.win_probability,
            "kelly": analysis.kelly_fraction,
            "verdict": verdict_map[analysis.recommendation],
            "confidence": analysis.confidence.value,
        }


# 유틸리티 함수
def calculate_position_size(
    capital: float,
    risk_per_trade: float,
    entry_price: float,
    stop_loss: float
) -> dict:
    """
    리스크 기반 포지션 크기 계산

    Args:
        capital: 총 자본
        risk_per_trade: 거래당 리스크 비율 (예: 0.02 = 2%)
        entry_price: 진입가
        stop_loss: 손절가

    Returns:
        dict: {position_size, quantity, risk_amount}
    """
    risk_amount = capital * risk_per_trade
    price_risk = abs(entry_price - stop_loss)

    if price_risk <= 0:
        return {"position_size": 0, "quantity": 0, "risk_amount": 0}

    quantity = risk_amount / price_risk
    position_size = quantity * entry_price

    return {
        "position_size": round(position_size, 0),
        "quantity": round(quantity, 8),
        "risk_amount": round(risk_amount, 0),
    }


if __name__ == "__main__":
    # 테스트
    calc = ExpectedValueCalculator()

    # 테스트 케이스 1: 좋은 셋업
    setup1 = TradeSetup(
        symbol="BTC/KRW",
        side="long",
        entry_price=100_000_000,
        stop_loss=97_000_000,    # -3%
        take_profit=109_000_000   # +9% (1:3 손익비)
    )

    result1 = calc.analyze(setup1, {"rsi": 35, "trend_direction": "up"})
    print("=== 테스트 1: 좋은 셋업 ===")
    print(f"기대값: {result1.expected_value}%")
    print(f"손익비: 1:{result1.risk_reward_ratio}")
    print(f"추천: {result1.recommendation.value}")
    print(f"근거: {result1.reasoning}")
    print()

    # 테스트 케이스 2: 나쁜 셋업
    setup2 = TradeSetup(
        symbol="BTC/KRW",
        side="long",
        entry_price=100_000_000,
        stop_loss=95_000_000,    # -5%
        take_profit=102_000_000   # +2% (1:0.4 손익비)
    )

    result2 = calc.analyze(setup2, {"rsi": 72, "trend_direction": "down"})
    print("=== 테스트 2: 나쁜 셋업 ===")
    print(f"기대값: {result2.expected_value}%")
    print(f"손익비: 1:{result2.risk_reward_ratio}")
    print(f"추천: {result2.recommendation.value}")
    print(f"근거: {result2.reasoning}")
    print()

    # 빠른 평가 테스트
    print("=== 빠른 평가 ===")
    quick = calc.quick_evaluate(
        entry_price=100_000_000,
        stop_loss=98_000_000,
        take_profit=106_000_000
    )
    print(quick)
