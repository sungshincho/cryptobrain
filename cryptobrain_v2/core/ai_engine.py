"""
CryptoBrain V2 - AI 분석 엔진
초개인화된 Gemini 기반 투자 어드바이저
"""
import google.generativeai as genai
from typing import Optional
from datetime import datetime

from ..database.models import InvestorProfile, PortfolioSummary
from ..config.settings import GEMINI_MODEL, GOOGLE_API_KEY


class AIEngine:
    """초개인화 AI 분석 엔진"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        profile: Optional[InvestorProfile] = None,
        portfolio: Optional[PortfolioSummary] = None,
        trade_stats: Optional[dict] = None
    ):
        """
        Args:
            api_key: Google AI API 키
            profile: 투자자 프로필
            portfolio: 포트폴리오 요약
            trade_stats: 거래 통계
        """
        self.api_key = api_key or GOOGLE_API_KEY
        self.profile = profile
        self.portfolio = portfolio
        self.trade_stats = trade_stats or {}

        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(GEMINI_MODEL)
        else:
            self.model = None

    def set_profile(self, profile: InvestorProfile):
        """프로필 설정"""
        self.profile = profile

    def set_portfolio(self, portfolio: PortfolioSummary):
        """포트폴리오 설정"""
        self.portfolio = portfolio

    def set_trade_stats(self, stats: dict):
        """거래 통계 설정"""
        self.trade_stats = stats

    def _build_personalized_prompt(self) -> str:
        """개인화된 시스템 프롬프트 생성"""
        if not self.profile:
            return self._get_default_prompt()

        profile = self.profile
        portfolio = self.portfolio
        stats = self.trade_stats

        # 포트폴리오 정보
        portfolio_section = ""
        if portfolio:
            allocation_str = ", ".join([
                f"{k}({v*100:.0f}%)" for k, v in portfolio.allocation.items()
            ])
            portfolio_section = f"""
[현재 포트폴리오]
- 총 투자금: {portfolio.total_invested:,.0f}원
- 현재 평가금: {portfolio.total_value:,.0f}원
- 수익률: {portfolio.total_pnl_pct:+.1f}%
- 현금 비중: {portfolio.allocation.get('현금', 0) * 100:.0f}%
- 보유 종목: {allocation_str}
- 집중 리스크: {portfolio.concentration_risk}
"""

        # 거래 통계 정보
        stats_section = ""
        if stats and stats.get("total_closed_trades", 0) > 0:
            stats_section = f"""
[거래 성과 통계]
- 총 거래: {stats.get('total_trades', 0)}회
- 승률: {stats.get('win_rate', 0):.1f}%
- 손익비: {stats.get('profit_factor', 0):.2f}
- 평균 수익 (승리 시): {stats.get('avg_win', 0):,.0f}원
- 평균 손실 (패배 시): {stats.get('avg_loss', 0):,.0f}원
- 최대 수익 거래: {stats.get('best_trade', 0):,.0f}원
- 최대 손실 거래: {stats.get('worst_trade', 0):,.0f}원
"""

        # 강점/약점 분석 (거래 통계 기반)
        strengths = []
        weaknesses = []

        if stats.get("win_rate", 0) >= 60:
            strengths.append(f"승률 {stats['win_rate']:.1f}%로 우수한 종목 선정력")
        elif stats.get("win_rate", 0) < 40:
            weaknesses.append(f"승률 {stats['win_rate']:.1f}%로 종목 선정 개선 필요")

        if stats.get("profit_factor", 0) >= 2.0:
            strengths.append(f"손익비 {stats['profit_factor']:.2f}로 탁월한 리스크 관리")
        elif stats.get("profit_factor", 0) < 1.0:
            weaknesses.append("손실이 수익보다 큼 - 손절 타이밍 개선 필요")

        # 프로필 기반 주의사항
        if profile.past_major_mistakes:
            weaknesses.extend([f"과거 실수: {m}" for m in profile.past_major_mistakes[:3]])

        sw_section = ""
        if strengths or weaknesses:
            sw_section = f"""
[이 투자자의 강점]
{chr(10).join(['- ' + s for s in strengths]) if strengths else '- 아직 충분한 데이터 없음'}

[이 투자자의 약점 - 주의해서 조언할 것]
{chr(10).join(['- ' + w for w in weaknesses]) if weaknesses else '- 아직 충분한 데이터 없음'}
"""

        prompt = f"""당신은 'CryptoBrain', {profile.experience_years}년차 투자자를 위한 개인 투자 어드바이저입니다.

═══════════════════════════════════════════════════════════
📋 이 투자자에 대해 알고 있는 정보
═══════════════════════════════════════════════════════════

[기본 프로필]
- 총 자본: {profile.total_capital:,}원
- 월 수입: {profile.monthly_income:,}원
- 투자 목표: {profile.investment_goal}
- 투자 기간: {profile.investment_horizon}
- 최대 감내 손실: {profile.max_loss_tolerance * 100:.0f}%
- 1회 리스크: {profile.risk_per_trade * 100:.1f}%
- 리스크 성향: {profile.risk_tolerance}
- 거래 스타일: {profile.trading_style}
- 거래 빈도: {profile.trading_frequency}
- 하루 투자 가능 시간: {profile.available_time_per_day}분
- 기술적 분석 수준: {profile.technical_analysis_skill}
- 선호 코인: {', '.join(profile.preferred_coins)}
{portfolio_section}
{stats_section}
{sw_section}

═══════════════════════════════════════════════════════════
🎯 조언 원칙 (이 투자자 맞춤)
═══════════════════════════════════════════════════════════

1. **리스크 맞춤**: 최대 {profile.max_loss_tolerance * 100:.0f}% 손실만 감내 가능합니다.
   이를 초과하는 리스크의 거래는 추천하지 마세요.

2. **시간 고려**: 하루 {profile.available_time_per_day}분만 차트를 볼 수 있습니다.
   잦은 모니터링이 필요한 전략은 피하세요.

3. **경험 수준**: {profile.technical_analysis_skill} 수준입니다.
   너무 복잡한 전략이나 용어는 쉽게 설명해주세요.

4. **과거 실수 방지**: {', '.join(profile.past_major_mistakes) if profile.past_major_mistakes else '없음'}
   이 실수들을 반복하지 않도록 경고해주세요.

5. **포지션 사이즈**: 1회 거래당 {profile.risk_per_trade * 100:.1f}%의 리스크만 사용하세요.

6. **희망적 해석 금지**: 냉정하고 객관적으로 분석하세요.
   불확실하면 "관망"을 권유하세요.

═══════════════════════════════════════════════════════════
📝 응답 형식
═══════════════════════════════════════════════════════════

## 시장 분석
(현재 상황 요약)

## 맞춤 조언
(이 투자자의 성향/상황을 고려한 구체적 조언)

## 매매 의견
- 의견: 매수 / 매도 / 관망
- 신뢰도: 상 / 중 / 하
- 근거: (1~2문장)

## 실행 계획 (매수/매도 시에만)
- 진입가:
- 목표가:
- 손절가:
- 추천 금액: (자본금과 리스크 기반)
- 예상 손실: (손절 시)
- 예상 수익: (목표가 도달 시)

## ⚠️ 개인 주의사항
(이 투자자가 특히 조심해야 할 점)
"""
        return prompt

    def _get_default_prompt(self) -> str:
        """기본 시스템 프롬프트"""
        return """당신은 'CryptoBrain', 20년 경력의 암호화폐 퀀트 트레이더입니다.

[분석 원칙]
1. 데이터에 근거한 분석만 합니다. 추측하지 않습니다.
2. 모든 매수 추천에는 반드시 진입가, 목표가, 손절가를 제시합니다.
3. 불확실하면 "판단 보류" 또는 "추가 확인 필요"라고 말합니다.
4. 희망적 해석(Hopium)을 경계하고 냉정하게 분석합니다.

[응답 형식]
## 시장 분석
(현재 상황 요약)

## 매매 의견
- 의견: 매수 / 매도 / 관망
- 신뢰도: 상 / 중 / 하
- 근거: (1~2문장)

## 실행 계획 (매수/매도 시에만)
- 진입가:
- 목표가:
- 손절가:

## 리스크 요인
(주의해야 할 점)
"""

    def analyze_market(
        self,
        market_data: dict,
        technical_signals: Optional[dict] = None
    ) -> str:
        """
        시장 종합 분석

        Args:
            market_data: 시장 데이터 {symbol: {price, rsi, trend, ...}}
            technical_signals: 기술적 분석 시그널

        Returns:
            AI 분석 결과
        """
        if not self.model:
            return "API 키가 설정되지 않았습니다."

        # 시장 데이터 문자열 생성
        market_context = self._format_market_data(market_data)

        # 기술적 분석 문자열
        ta_context = ""
        if technical_signals:
            ta_context = self._format_technical_signals(technical_signals)

        # 프롬프트 구성
        system_prompt = self._build_personalized_prompt()

        user_prompt = f"""
[실시간 시장 데이터]
{market_context}

{ta_context}

위 데이터를 종합적으로 분석하여, 오늘 매매할 만한 종목이 있는지 알려주세요.
없다면 관망을 권유해주세요.
"""

        try:
            response = self.model.generate_content([system_prompt, user_prompt])
            return response.text
        except Exception as e:
            return f"AI 분석 중 오류가 발생했습니다: {e}"

    def analyze_symbol(
        self,
        symbol: str,
        market_data: dict,
        technical_signals: dict
    ) -> str:
        """
        특정 종목 분석

        Args:
            symbol: 분석할 심볼
            market_data: 해당 심볼의 시장 데이터
            technical_signals: 기술적 분석 시그널

        Returns:
            AI 분석 결과
        """
        if not self.model:
            return "API 키가 설정되지 않았습니다."

        system_prompt = self._build_personalized_prompt()

        # 포트폴리오 내 해당 종목 보유 여부 확인
        holding_info = ""
        if self.portfolio:
            for pos in self.portfolio.positions:
                if pos.symbol == symbol:
                    holding_info = f"""
[현재 보유 상황]
- 보유 수량: {pos.quantity}
- 평균 매수가: {pos.avg_entry_price:,.0f}원
- 현재 손익: {pos.unrealized_pnl:,.0f}원 ({pos.unrealized_pnl_pct:+.1f}%)
"""
                    break

        user_prompt = f"""
[{symbol} 분석 요청]

[시장 데이터]
- 현재가: {market_data.get('price', 0):,.0f}원
- RSI: {market_data.get('rsi', 50):.1f}
- 추세: {market_data.get('trend', 'neutral')}
- 변동률: {market_data.get('change', 0):+.2f}%

[기술적 분석]
- 종합 점수: {technical_signals.get('strength', 50)}/100
- 추세: {technical_signals.get('trend', 'neutral')}
- RSI 시그널: {technical_signals.get('rsi_signal', 'neutral')}
- MACD 시그널: {technical_signals.get('macd_signal', 'neutral')}
- 지지선: {technical_signals.get('support_levels', [])}
- 저항선: {technical_signals.get('resistance_levels', [])}
- ATR: {technical_signals.get('atr', 0):,.0f}원 ({technical_signals.get('atr_pct', 0):.2f}%)
{holding_info}

이 종목에 대해 상세 분석해주세요.
"""

        try:
            response = self.model.generate_content([system_prompt, user_prompt])
            return response.text
        except Exception as e:
            return f"AI 분석 중 오류가 발생했습니다: {e}"

    def chat(
        self,
        user_message: str,
        market_context: str = ""
    ) -> str:
        """
        대화형 질의응답

        Args:
            user_message: 사용자 메시지
            market_context: 시장 컨텍스트 (선택)

        Returns:
            AI 응답
        """
        if not self.model:
            return "API 키가 설정되지 않았습니다."

        system_prompt = self._build_personalized_prompt()

        context = ""
        if market_context:
            context = f"\n[현재 시장 상황]\n{market_context}\n"

        full_prompt = f"{system_prompt}\n{context}\n[사용자 질문]\n{user_message}"

        try:
            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"AI 응답 중 오류가 발생했습니다: {e}"

    def get_personalized_warning(
        self,
        proposed_action: str,
        symbol: str,
        current_state: Optional[dict] = None
    ) -> str:
        """
        개인 맞춤 경고 메시지 생성

        Args:
            proposed_action: 예정 행동 ("buy", "sell")
            symbol: 대상 심볼
            current_state: 현재 상태 정보

        Returns:
            경고 메시지
        """
        warnings = []

        if not self.profile:
            return ""

        # 시간대 체크
        current_hour = datetime.now().hour
        try:
            start_hour = int(self.profile.active_hours_start.split(":")[0])
            end_hour = int(self.profile.active_hours_end.split(":")[0])

            if not (start_hour <= current_hour <= end_hour):
                warnings.append(
                    f"현재 시간({current_hour}시)은 설정한 활성 시간"
                    f"({self.profile.active_hours_start}~{self.profile.active_hours_end}) 밖입니다."
                )
        except (ValueError, AttributeError):
            pass

        # 과거 실수 패턴 체크
        if proposed_action == "buy" and "FOMO매수" in self.profile.past_major_mistakes:
            warnings.append("FOMO 매수 성향이 있습니다. 충분히 분석하셨나요?")

        if proposed_action == "sell" and "조기익절" in self.profile.past_major_mistakes:
            warnings.append("조기 익절 성향이 있습니다. 목표가까지 기다려보세요.")

        # 거래 통계 기반 체크
        if self.trade_stats:
            # 연속 손실 체크 (간단한 구현)
            if self.trade_stats.get("recent_losses", 0) >= 2:
                warnings.append(
                    f"최근 연속 {self.trade_stats['recent_losses']}회 손실 중입니다. "
                    "복수 매매 주의!"
                )

        # 포트폴리오 집중도 체크
        if self.portfolio and proposed_action == "buy":
            coin = symbol.split("/")[0]
            current_alloc = self.portfolio.allocation.get(coin, 0)
            if current_alloc >= 0.3:
                warnings.append(
                    f"{coin} 비중이 이미 {current_alloc*100:.0f}%입니다. "
                    "추가 매수 시 집중 리스크 주의!"
                )

        if warnings:
            return "\n".join([f"⚠️ {w}" for w in warnings])
        return ""

    def _format_market_data(self, data: dict) -> str:
        """시장 데이터 포맷팅"""
        lines = []
        for symbol, info in data.items():
            trend_emoji = "📈" if info.get("trend") == "bullish" else "📉"
            lines.append(
                f"- {symbol}: {info.get('price', 0):,.0f}원 "
                f"(RSI: {info.get('rsi', 50):.1f}, {trend_emoji})"
            )
        return "\n".join(lines)

    def _format_technical_signals(self, signals: dict) -> str:
        """기술적 시그널 포맷팅"""
        return f"""
[기술적 분석 시그널]
- 종합 점수: {signals.get('strength', 50)}/100
- 추세: {signals.get('trend', 'neutral')}
- RSI: {signals.get('rsi_signal', 'neutral')} ({signals.get('rsi_value', 50)})
- MACD: {signals.get('macd_signal', 'neutral')}
- 볼린저: {signals.get('bb_signal', 'neutral')}
- 거래량: {signals.get('volume_signal', 'normal')}
- 추천: {signals.get('recommendation', 'hold')}
"""


if __name__ == "__main__":
    # 테스트 (API 키 없이)
    from ..database.models import InvestorProfile, PortfolioSummary, Position

    profile = InvestorProfile(
        total_capital=5000000,
        monthly_income=3000000,
        investment_goal="장기자산증식",
        risk_tolerance="moderate",
        risk_per_trade=0.02,
        trading_style="swing",
        experience_years=2.0,
        technical_analysis_skill="intermediate",
        past_major_mistakes=["FOMO매수", "손절못함"],
        preferred_coins=["BTC", "ETH"],
    )

    portfolio = PortfolioSummary(
        total_invested=3000000,
        total_value=3300000,
        cash_balance=2000000,
        positions=[
            Position(
                symbol="BTC/KRW",
                quantity=0.05,
                avg_entry_price=50000000,
                current_price=55000000
            )
        ]
    )

    trade_stats = {
        "total_trades": 20,
        "total_closed_trades": 15,
        "win_rate": 60.0,
        "profit_factor": 1.8,
        "avg_win": 100000,
        "avg_loss": -60000,
        "best_trade": 300000,
        "worst_trade": -150000,
    }

    engine = AIEngine(profile=profile, portfolio=portfolio, trade_stats=trade_stats)

    print("=== 개인화된 시스템 프롬프트 ===")
    print(engine._build_personalized_prompt())

    print("\n=== 경고 메시지 테스트 ===")
    warning = engine.get_personalized_warning("buy", "ETH/KRW")
    print(warning if warning else "경고 없음")
