"""
CryptoBrain V2 - 포지션 계산기
자본금과 리스크에 기반한 적정 매수 수량 계산
"""
from dataclasses import dataclass
from typing import Optional

from ..config.settings import (
    DEFAULT_RISK_PER_TRADE,
    MAX_RISK_PER_TRADE,
    ATR_STOP_MULTIPLIER,
)


@dataclass
class PositionResult:
    """포지션 계산 결과"""
    position_size: float        # 매수 수량
    position_value: float       # 매수 금액
    risk_amount: float          # 리스크 금액
    stop_loss_price: float      # 손절가
    target_1to2: float          # 1:2 목표가
    target_1to3: float          # 1:3 목표가
    risk_reward_ratio: float    # 손익비
    position_pct: float         # 자본 대비 포지션 비율


class PositionSizer:
    """포지션 사이즈 계산기"""

    def __init__(
        self,
        capital: float,
        risk_per_trade: float = DEFAULT_RISK_PER_TRADE
    ):
        """
        Args:
            capital: 총 자본금
            risk_per_trade: 1회 리스크 비율 (기본 2%)
        """
        self.capital = capital
        self.risk_per_trade = min(risk_per_trade, MAX_RISK_PER_TRADE)

    @property
    def risk_amount(self) -> float:
        """허용 리스크 금액"""
        return self.capital * self.risk_per_trade

    def calculate_position(
        self,
        entry_price: float,
        stop_loss_price: float,
        target_price: Optional[float] = None
    ) -> PositionResult:
        """
        포지션 크기 계산

        Args:
            entry_price: 진입 예정가
            stop_loss_price: 손절가
            target_price: 목표가 (선택)

        Returns:
            PositionResult
        """
        if entry_price <= 0 or stop_loss_price <= 0:
            raise ValueError("가격은 0보다 커야 합니다")

        # 손절폭 계산
        stop_loss_distance = abs(entry_price - stop_loss_price)

        if stop_loss_distance == 0:
            raise ValueError("손절가는 진입가와 달라야 합니다")

        # 매수 수량 계산: 리스크 금액 / 손절폭
        position_size = self.risk_amount / stop_loss_distance

        # 매수 금액
        position_value = position_size * entry_price

        # 포지션 비율
        position_pct = (position_value / self.capital) * 100

        # 목표가 계산 (1:2, 1:3 손익비)
        is_long = entry_price > stop_loss_price

        if is_long:
            target_1to2 = entry_price + (stop_loss_distance * 2)
            target_1to3 = entry_price + (stop_loss_distance * 3)
        else:
            target_1to2 = entry_price - (stop_loss_distance * 2)
            target_1to3 = entry_price - (stop_loss_distance * 3)

        # 실제 손익비 계산
        if target_price:
            profit_distance = abs(target_price - entry_price)
            risk_reward_ratio = profit_distance / stop_loss_distance
        else:
            risk_reward_ratio = 2.0  # 기본 1:2

        return PositionResult(
            position_size=position_size,
            position_value=position_value,
            risk_amount=self.risk_amount,
            stop_loss_price=stop_loss_price,
            target_1to2=target_1to2,
            target_1to3=target_1to3,
            risk_reward_ratio=risk_reward_ratio,
            position_pct=position_pct,
        )

    def calculate_stop_loss(
        self,
        entry_price: float,
        atr: float,
        multiplier: float = ATR_STOP_MULTIPLIER,
        is_long: bool = True
    ) -> float:
        """
        ATR 기반 손절가 계산

        Args:
            entry_price: 진입가
            atr: ATR 값
            multiplier: ATR 배수 (기본 1.5)
            is_long: 롱 포지션 여부

        Returns:
            손절가
        """
        stop_distance = atr * multiplier

        if is_long:
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance

    def calculate_from_atr(
        self,
        entry_price: float,
        atr: float,
        multiplier: float = ATR_STOP_MULTIPLIER,
        is_long: bool = True,
        target_rr: float = 2.0
    ) -> PositionResult:
        """
        ATR 기반 전체 포지션 계산

        Args:
            entry_price: 진입가
            atr: ATR 값
            multiplier: ATR 배수
            is_long: 롱 포지션 여부
            target_rr: 목표 손익비

        Returns:
            PositionResult
        """
        stop_loss = self.calculate_stop_loss(
            entry_price, atr, multiplier, is_long
        )

        stop_distance = abs(entry_price - stop_loss)

        if is_long:
            target_price = entry_price + (stop_distance * target_rr)
        else:
            target_price = entry_price - (stop_distance * target_rr)

        return self.calculate_position(entry_price, stop_loss, target_price)

    def get_recommended_size_by_conviction(
        self,
        entry_price: float,
        stop_loss_price: float,
        conviction: str = "medium"
    ) -> PositionResult:
        """
        확신도에 따른 포지션 사이즈 조절

        Args:
            entry_price: 진입가
            stop_loss_price: 손절가
            conviction: 확신도 ("low", "medium", "high")

        Returns:
            PositionResult
        """
        conviction_multipliers = {
            "low": 0.5,      # 리스크의 50%만 사용
            "medium": 1.0,   # 기본 리스크
            "high": 1.5,     # 리스크의 150% 사용 (최대 5%까지)
        }

        multiplier = conviction_multipliers.get(conviction, 1.0)
        adjusted_risk = min(
            self.risk_per_trade * multiplier,
            MAX_RISK_PER_TRADE
        )

        # 임시로 리스크 비율 조정
        original_risk = self.risk_per_trade
        self.risk_per_trade = adjusted_risk

        result = self.calculate_position(entry_price, stop_loss_price)

        # 원래대로 복원
        self.risk_per_trade = original_risk

        return result

    def format_result(self, result: PositionResult, symbol: str = "") -> str:
        """결과를 텍스트로 포맷팅"""
        text = f"""
📊 포지션 계산 결과 {f'({symbol})' if symbol else ''}

💰 자본금: {self.capital:,.0f}원
📉 1회 리스크: {self.risk_per_trade * 100:.1f}% ({self.risk_amount:,.0f}원)

📌 매수 수량: {result.position_size:.8f}
💵 매수 금액: {result.position_value:,.0f}원
📊 포지션 비율: {result.position_pct:.1f}%

🎯 손절가: {result.stop_loss_price:,.0f}원
🎯 목표가 (1:2): {result.target_1to2:,.0f}원
🎯 목표가 (1:3): {result.target_1to3:,.0f}원

⚖️ 손익비: 1:{result.risk_reward_ratio:.1f}
"""
        return text.strip()

    def validate_position(
        self,
        result: PositionResult,
        max_position_pct: float = 40.0
    ) -> dict:
        """
        포지션 유효성 검사

        Args:
            result: 포지션 계산 결과
            max_position_pct: 최대 허용 포지션 비율

        Returns:
            검증 결과
        """
        warnings = []
        is_valid = True

        # 포지션 비율 체크
        if result.position_pct > max_position_pct:
            warnings.append(
                f"포지션 비율({result.position_pct:.1f}%)이 "
                f"최대 허용치({max_position_pct}%)를 초과합니다"
            )

        # 손익비 체크
        if result.risk_reward_ratio < 1.5:
            warnings.append(
                f"손익비({result.risk_reward_ratio:.1f})가 1.5 미만입니다. "
                "더 좋은 진입점을 찾아보세요."
            )

        # 리스크 금액 체크
        if result.risk_amount > self.capital * 0.05:
            warnings.append("1회 리스크가 자본금의 5%를 초과합니다")
            is_valid = False

        return {
            "is_valid": is_valid and len(warnings) == 0,
            "warnings": warnings,
        }


if __name__ == "__main__":
    # 테스트
    capital = 5000000  # 500만원
    sizer = PositionSizer(capital, risk_per_trade=0.02)

    print("=== 기본 포지션 계산 ===")
    result = sizer.calculate_position(
        entry_price=50000000,   # 비트코인 5천만원
        stop_loss_price=48000000  # 손절 4800만원
    )
    print(sizer.format_result(result, "BTC/KRW"))

    print("\n=== ATR 기반 계산 ===")
    result_atr = sizer.calculate_from_atr(
        entry_price=50000000,
        atr=1000000,  # ATR 100만원
        multiplier=1.5,
        is_long=True,
        target_rr=2.0
    )
    print(sizer.format_result(result_atr, "BTC/KRW"))

    print("\n=== 확신도별 계산 ===")
    for conviction in ["low", "medium", "high"]:
        result_conv = sizer.get_recommended_size_by_conviction(
            entry_price=50000000,
            stop_loss_price=48000000,
            conviction=conviction
        )
        print(f"\n{conviction.upper()} 확신도:")
        print(f"  매수금액: {result_conv.position_value:,.0f}원")
        print(f"  포지션비율: {result_conv.position_pct:.1f}%")

    print("\n=== 유효성 검사 ===")
    validation = sizer.validate_position(result)
    print(f"유효: {validation['is_valid']}")
    if validation["warnings"]:
        for w in validation["warnings"]:
            print(f"  ⚠️ {w}")
