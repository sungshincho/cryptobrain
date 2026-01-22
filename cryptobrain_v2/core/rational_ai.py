"""
CryptoBrain V3 - 이성적 트레이딩 AI

모든 판단은 기대값과 확률에 기반
감정적 요청은 필터링하고 교육
"""
import google.generativeai as genai
import pandas as pd
from typing import Optional
from datetime import datetime

from .decision_engine.expected_value import (
    ExpectedValueCalculator,
    TradeSetup,
    EVAnalysis,
    Recommendation,
)
from .decision_engine.market_analyzer import (
    MarketAnalyzer,
    MarketContext,
    MarketRegime,
)
from .decision_engine.emotion_filter import (
    EmotionFilter,
    EmotionAnalysis,
    EmotionTracker,
)

# 시스템 프롬프트
RATIONAL_TRADER_SYSTEM_PROMPT = """
당신은 수학적 기대값에 기반한 냉철한 트레이딩 AI입니다.
당신의 유일한 목표는 **사용자가 장기적으로 수익을 내도록** 하는 것입니다.

═══════════════════════════════════════════════════════════════
🎯 핵심 원칙
═══════════════════════════════════════════════════════════════

1. **기대값(EV) 양수 거래만**
   - 모든 거래의 EV를 계산합니다
   - EV = (승률 × 수익) - (패률 × 손실)
   - EV < 0인 거래는 절대 추천하지 않습니다

2. **손익비(R:R) 최소 1:1.5**
   - 손익비가 1:1.5 미만인 거래는 추천하지 않습니다
   - 이상적인 손익비는 1:2 이상입니다

3. **확률 기반 의사결정**
   - "느낌"이나 "감"으로 판단하지 않습니다
   - 과거 데이터와 통계에 기반합니다
   - 불확실하면 "모른다"고 합니다

4. **리스크 관리 최우선**
   - 단일 거래 리스크: 자본의 1-2% 이하
   - 총 노출 리스크: 자본의 10% 이하
   - 손절은 진입 전 반드시 설정

5. **감정 거래 차단**
   - FOMO 요청 → 거절
   - 복수 매매 → 거절
   - 올인 요청 → 거절
   - 사용자가 화나도 원칙 준수

═══════════════════════════════════════════════════════════════
🚫 절대 하지 않는 것
═══════════════════════════════════════════════════════════════

- 근거 없는 가격 예측 ("$100K 간다")
- 감정에 호소 ("좋은 기회예요!")
- 모호한 조언 ("지켜보세요")
- 책임 회피 ("본인 판단에...")
- FOMO 조장 ("지금 안 사면 늦어요")

═══════════════════════════════════════════════════════════════
✅ 항상 하는 것
═══════════════════════════════════════════════════════════════

- 구체적 수치 제시 (진입가, 손절가, 목표가)
- 기대값/손익비 계산 결과 공유
- 거래 거절 시 명확한 이유 설명
- 더 좋은 대안 제시
- 틀릴 수 있음을 인정

═══════════════════════════════════════════════════════════════
📝 응답 형식
═══════════════════════════════════════════════════════════════

[거래 추천 시]
## 📊 분석 결과
- 기대값: +X.X%
- 손익비: 1:X.X
- 추정 승률: XX%
- 신뢰도: 상/중/하

## ✅ 실행 계획
- 진입가: ₩XX,XXX
- 손절가: ₩XX,XXX (리스크 X%)
- 목표가: ₩XX,XXX (1차), ₩XX,XXX (2차)
- 포지션 크기: 자본의 X%

## ⚠️ 리스크
- (잠재적 위험 요소)

[거래 거절 시]
## ❌ 이 거래를 추천하지 않습니다

**이유:**
- (구체적 이유 1)
- (구체적 이유 2)

**대안:**
- (더 좋은 기회 또는 대기 조건)
"""


class RationalTradingAI:
    """
    이성적 트레이딩 AI

    모든 판단은 기대값과 확률에 기반
    감정적 요청은 필터링
    """

    def __init__(
        self,
        api_key: str,
        user_capital: float = 1_000_000,
        model_name: str = "gemini-3-flash-preview"
    ):
        """
        Args:
            api_key: Google AI API 키
            user_capital: 사용자 총 자본
            model_name: Gemini 모델명
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.capital = user_capital
        self.model_name = model_name

        # 핵심 엔진들
        self.ev_calculator = ExpectedValueCalculator()
        self.market_analyzer = MarketAnalyzer()
        self.emotion_filter = EmotionFilter()
        self.emotion_tracker = EmotionTracker()

        # 대화 기록
        self.chat_history = []

    def process_request(
        self,
        user_message: str,
        market_data: dict = None,
        ohlcv_data: pd.DataFrame = None,
        last_trade: dict = None
    ) -> str:
        """
        사용자 요청 처리 메인 함수

        Args:
            user_message: 사용자 입력
            market_data: 현재 시장 데이터
            ohlcv_data: OHLCV DataFrame
            last_trade: 마지막 거래 정보

        Returns:
            str: AI 응답
        """
        market_data = market_data or {}

        # 1. 감정 필터링
        recent_move = market_data.get('recent_move', {})

        emotion_analysis = self.emotion_filter.analyze_request(
            user_message,
            recent_move,
            last_trade
        )

        # 감정 추적
        self.emotion_tracker.record(emotion_analysis)

        # 강제 휴식 필요 체크
        if self.emotion_tracker.should_force_break():
            return self._generate_force_break_response()

        # 2. 감정적 요청이면 교육 + 대안 제시
        if not emotion_analysis.is_rational:
            return self._handle_emotional_request(
                user_message, emotion_analysis, market_data
            )

        # 3. 시장 분석
        market_context = None
        if ohlcv_data is not None and len(ohlcv_data) > 0:
            market_context = self.market_analyzer.analyze(
                ohlcv_data,
                market_data.get('symbol', '')
            )

        # 4. 거래 의도 파악
        trade_setup = self._extract_trade_setup(user_message, market_data)

        if trade_setup:
            # 기대값 분석
            context_dict = market_context.to_dict() if market_context else {}
            ev_analysis = self.ev_calculator.analyze(trade_setup, context_dict)
            return self._generate_trade_response(trade_setup, ev_analysis, market_context)

        # 5. 일반 분석 요청
        return self._generate_analysis_response(
            user_message, market_context, market_data
        )

    def analyze_trade_setup(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        market_context: dict = None
    ) -> EVAnalysis:
        """
        거래 셋업 분석 (직접 호출용)

        Returns:
            EVAnalysis: 기대값 분석 결과
        """
        setup = TradeSetup(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit
        )

        return self.ev_calculator.analyze(setup, market_context or {})

    def evaluate_opportunity(
        self,
        symbol: str,
        ohlcv: pd.DataFrame,
        current_price: float = None
    ) -> str:
        """
        특정 코인의 현재 기회 평가
        "비트코인 어때?" 같은 질문에 응답

        Returns:
            str: 분석 결과 텍스트
        """
        context = self.market_analyzer.analyze(ohlcv, symbol)

        if current_price is None and len(ohlcv) > 0:
            current_price = ohlcv.iloc[-1]['close']

        prompt = f"""
{RATIONAL_TRADER_SYSTEM_PROMPT}

═══════════════════════════════════════════════════════════════
📊 {symbol} 시장 분석 요청
═══════════════════════════════════════════════════════════════

[현재가]
{current_price:,.0f}원

[시장 국면]
{context.regime.value}

[추세]
방향: {context.trend_direction}
강도: {context.trend_strength.value}

[기술적 지표]
- RSI: {context.rsi:.1f} ({context.rsi_signal})
- MACD: {context.macd_signal}
- 이평선 정렬: {context.ma_alignment}

[지지/저항]
- 가장 가까운 지지선: {context.nearest_support:,.0f}원 (현재가 대비 {context.distance_to_support_pct:.1f}%)
- 가장 가까운 저항선: {context.nearest_resistance:,.0f}원 (현재가 대비 {context.distance_to_resistance_pct:.1f}%)

[변동성]
- ATR: {context.atr_percent:.2f}%
- 변동성 수준: {context.volatility_regime}

[거래량]
- 추세: {context.volume_trend}
- 이상 거래량: {'⚠️ 감지됨' if context.volume_anomaly else '정상'}

[시스템 분석 결과]
추천 전략: {context.recommended_strategy}
매수 유리 점수: {context.bullish_score:.0f}/100
매도 유리 점수: {context.bearish_score:.0f}/100

[분석 근거]
{chr(10).join(context.reasoning)}

위 분석을 바탕으로:
1. 현재 이 코인의 상태를 요약하세요
2. 지금 진입해도 되는지 명확히 답하세요 (예/아니오/조건부)
3. 진입한다면 구체적인 진입가, 손절가, 목표가를 제시하세요
4. 진입하지 않는다면 어떤 조건이 충족되어야 하는지 알려주세요
5. 기대값과 손익비 추정치를 포함하세요

한국어로 응답하세요.
"""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"AI 응답 생성 오류: {str(e)}"

    def _handle_emotional_request(
        self,
        user_message: str,
        emotion: EmotionAnalysis,
        market_data: dict
    ) -> str:
        """감정적 요청 처리"""

        # 감정 리포트 생성
        emotion_report = self.emotion_filter.get_emotion_report(emotion)

        if emotion.should_block:
            # 심각한 감정 상태 - AI 없이 직접 응답
            return f"""
{emotion_report}

🛑 **지금은 거래하지 마세요**

감정적 거래는 손실의 주요 원인입니다.
통계적으로 FOMO/공포/복수 매매의 승률은 35% 미만입니다.

{emotion.alternative_advice}

최소 30분간 차트를 끄고 다른 활동을 하신 후,
냉정하게 기대값을 계산하고 다시 판단하세요.
"""

        # AI로 교육적 응답 생성
        prompt = f"""
{RATIONAL_TRADER_SYSTEM_PROMPT}

═══════════════════════════════════════════════════════════════
⚠️ 감정적 요청 감지
═══════════════════════════════════════════════════════════════

[사용자 메시지]
"{user_message}"

[감지된 감정]
{', '.join(emotion.detected_emotions)}

[감정 점수]
{emotion.emotion_score:.1f}/1.0 {'(높음 - 주의 필요)' if emotion.emotion_score > 0.5 else '(보통)'}

[시스템 경고]
{chr(10).join(emotion.warnings)}

[제안된 대안]
{emotion.alternative_advice}

[현재 시장 상황]
{self._format_market_brief(market_data)}

위 상황을 고려하여:
1. 사용자의 감정을 공감하되, 위험성을 설명하세요
2. 왜 지금 이 거래가 위험한지 데이터로 보여주세요
3. 구체적인 대안을 제시하세요 (언제, 어떤 조건에서 진입해야 하는지)
4. 단호하지만 친절하게 말하세요

한국어로 응답하세요.
"""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"AI 응답 생성 오류: {str(e)}\n\n{emotion.alternative_advice}"

    def _generate_trade_response(
        self,
        setup: TradeSetup,
        ev: EVAnalysis,
        context: MarketContext = None
    ) -> str:
        """거래 분석 응답 생성"""

        if ev.recommendation == Recommendation.ENTER:
            return self._format_entry_recommendation(setup, ev, context)
        elif ev.recommendation == Recommendation.SKIP:
            return self._format_skip_recommendation(setup, ev, context)
        else:  # WAIT
            return self._format_wait_recommendation(setup, ev, context)

    def _format_entry_recommendation(
        self,
        setup: TradeSetup,
        ev: EVAnalysis,
        context: MarketContext = None
    ) -> str:
        """진입 추천 포맷"""

        # 포지션 크기 계산
        position_size = self.capital * ev.kelly_fraction
        risk_amount = self.capital * 0.02  # 2% 리스크

        side_text = "매수" if setup.side == "long" else "매도"
        confidence_text = {"high": "높음", "medium": "보통", "low": "낮음"}.get(ev.confidence.value, "보통")

        return f"""
## ✅ 거래 추천: {setup.symbol} {side_text}

### 📊 분석 결과
| 지표 | 값 | 평가 |
|------|-----|------|
| 기대값 | **+{ev.expected_value:.2f}%** | {'✅ 양호' if ev.expected_value > 1 else '⚠️ 보통'} |
| 손익비 | **1:{ev.risk_reward_ratio:.1f}** | {'✅ 우수' if ev.risk_reward_ratio >= 2 else '✅ 양호'} |
| 추정 승률 | **{ev.win_probability*100:.0f}%** | {'✅ 높음' if ev.win_probability > 0.55 else '⚠️ 보통'} |
| 신뢰도 | **{confidence_text}** | |

### ✅ 실행 계획
- **진입가**: {setup.entry_price:,.0f}원
- **손절가**: {setup.stop_loss:,.0f}원 (리스크 {setup.risk_percent:.1f}%)
- **1차 목표**: {setup.take_profit:,.0f}원 (+{setup.reward_percent:.1f}%)
- **포지션 크기**: {position_size:,.0f}원 (자본의 {ev.kelly_fraction*100:.1f}%)
- **최대 손실**: {risk_amount:,.0f}원 (자본의 2%)

### 📈 판단 근거
{chr(10).join(['- ' + r for r in ev.reasoning])}

### ⚠️ 주의사항
- 손절가 도달 시 **반드시 손절** (예외 없음)
- 시장 상황 급변 시 계획 재검토
- 이 분석은 확률적 추정이며, 손실 가능성 존재
"""

    def _format_skip_recommendation(
        self,
        setup: TradeSetup,
        ev: EVAnalysis,
        context: MarketContext = None
    ) -> str:
        """거래 거절 포맷"""

        support_price = context.nearest_support if context else setup.entry_price * 0.95

        return f"""
## ❌ 이 거래를 추천하지 않습니다

### 📊 분석 결과
| 지표 | 값 | 문제점 |
|------|-----|--------|
| 기대값 | **{ev.expected_value:+.2f}%** | {'❌ 마이너스' if ev.expected_value < 0 else '⚠️ 너무 낮음'} |
| 손익비 | **1:{ev.risk_reward_ratio:.1f}** | {'❌ 불리' if ev.risk_reward_ratio < 1 else '⚠️ 낮음'} |
| 추정 승률 | **{ev.win_probability*100:.0f}%** | {'❌ 낮음' if ev.win_probability < 0.4 else ''} |

### 🚫 거절 이유
{chr(10).join(['- ' + r for r in ev.reasoning])}

### 💡 대안
1. **더 좋은 진입점 대기**: 가격이 {support_price:,.0f}원 지지선까지 조정 시 재검토
2. **손익비 개선**: 손절을 더 가깝게, 목표를 더 멀게 조정
3. **다른 기회 탐색**: 현재 시장에서 기대값 양수인 셋업 찾기

### 📌 기억하세요
> 좋은 트레이더는 모든 기회에 뛰어들지 않습니다.
> 기대값이 확실히 양수인 거래만 선택합니다.
"""

    def _format_wait_recommendation(
        self,
        setup: TradeSetup,
        ev: EVAnalysis,
        context: MarketContext = None
    ) -> str:
        """대기 권고 포맷"""

        return f"""
## ⏸️ 조건 충족까지 대기하세요

### 📊 현재 분석
| 지표 | 값 | 상태 |
|------|-----|------|
| 기대값 | **{ev.expected_value:+.2f}%** | {'⚠️ 낮음' if ev.expected_value < 1 else '✅'} |
| 손익비 | **1:{ev.risk_reward_ratio:.1f}** | {'⚠️ 개선 필요' if ev.risk_reward_ratio < 1.5 else '✅'} |
| 추정 승률 | **{ev.win_probability*100:.0f}%** | {'⚠️ 낮음' if ev.win_probability < 0.45 else '✅'} |

### 📋 대기 이유
{chr(10).join(['- ' + r for r in ev.reasoning])}

### ⏰ 진입 조건
다음 조건이 충족되면 재검토하세요:
1. RSI 50 이하로 하락
2. 손익비 1:2 이상 확보 가능한 가격대
3. 거래량 증가와 함께 지지선 터치

### 💡 권장 행동
- 알림 설정하고 대기
- 다른 종목의 기회 탐색
- 급하게 진입하지 말 것
"""

    def _generate_analysis_response(
        self,
        user_message: str,
        context: MarketContext = None,
        market_data: dict = None
    ) -> str:
        """일반 분석 응답 생성"""

        market_brief = self._format_market_brief(market_data)
        context_brief = self._format_context_brief(context) if context else "시장 데이터 없음"

        prompt = f"""
{RATIONAL_TRADER_SYSTEM_PROMPT}

[사용자 질문]
{user_message}

[시장 데이터]
{market_brief}

[기술적 분석]
{context_brief}

위 정보를 바탕으로 질문에 답변하세요.
- 구체적인 수치 포함
- 기대값/손익비 관점에서 분석
- 모호한 답변 금지
- 필요시 "데이터가 부족하여 정확한 답변이 어렵습니다" 명시

한국어로 응답하세요.
"""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"AI 응답 생성 오류: {str(e)}"

    def _generate_force_break_response(self) -> str:
        """강제 휴식 권고 응답"""
        return """
🛑 **강제 휴식 권고**

연속 3회 이상 감정적 거래 요청이 감지되었습니다.

현재 심리 상태에서의 거래는 **높은 확률로 손실**로 이어집니다.

**권장 행동:**
1. 차트와 거래소 앱을 모두 종료하세요
2. 최소 2시간 동안 다른 활동을 하세요
3. 산책, 운동, 또는 취미 활동을 권장합니다
4. 충분히 냉정해진 후 다시 시작하세요

**기억하세요:**
- 시장은 항상 열려 있습니다
- 오늘 놓친 기회보다 내일의 자본이 더 중요합니다
- 감정적 거래의 승률은 35% 미만입니다

2시간 후에 다시 대화해주세요.
"""

    def _extract_trade_setup(self, message: str, market_data: dict) -> Optional[TradeSetup]:
        """메시지에서 거래 셋업 추출"""
        # 간단한 패턴 매칭 (실제로는 더 정교한 NLP 필요)
        import re

        # 가격 패턴
        price_pattern = r'(\d{1,3}(?:,?\d{3})*(?:\.\d+)?)\s*원?'

        # 진입가, 손절가, 목표가 추출 시도
        entry_match = re.search(r'진입.*?' + price_pattern, message)
        stop_match = re.search(r'손절.*?' + price_pattern, message)
        target_match = re.search(r'목표.*?' + price_pattern, message)

        if entry_match and stop_match and target_match:
            def parse_price(match):
                price_str = match.group(1).replace(',', '')
                return float(price_str)

            entry = parse_price(entry_match)
            stop = parse_price(stop_match)
            target = parse_price(target_match)

            side = "long" if target > entry else "short"

            return TradeSetup(
                symbol=market_data.get('symbol', 'UNKNOWN'),
                side=side,
                entry_price=entry,
                stop_loss=stop,
                take_profit=target
            )

        return None

    def _format_market_brief(self, market_data: dict) -> str:
        """시장 데이터 요약"""
        if not market_data:
            return "시장 데이터 없음"

        lines = []
        if 'symbol' in market_data:
            lines.append(f"종목: {market_data['symbol']}")
        if 'price' in market_data:
            lines.append(f"현재가: {market_data['price']:,.0f}원")
        if 'recent_move' in market_data:
            move = market_data['recent_move']
            if 'change_24h' in move:
                lines.append(f"24시간 변동: {move['change_24h']:+.1f}%")

        return "\n".join(lines) if lines else "시장 데이터 없음"

    def _format_context_brief(self, context: MarketContext) -> str:
        """컨텍스트 요약"""
        return f"""
시장 국면: {context.regime.value}
추세: {context.trend_direction} ({context.trend_strength.value})
RSI: {context.rsi:.1f} ({context.rsi_signal})
MACD: {context.macd_signal}
MA 정렬: {context.ma_alignment}
변동성: {context.volatility_regime}
매수 점수: {context.bullish_score:.0f}/100
매도 점수: {context.bearish_score:.0f}/100
추천 전략: {context.recommended_strategy}
"""


# 편의 함수
def quick_ev_check(
    entry: float,
    stop: float,
    target: float,
    side: str = "long"
) -> dict:
    """빠른 기대값 체크"""
    calc = ExpectedValueCalculator()
    return calc.quick_evaluate(entry, stop, target, side)


if __name__ == "__main__":
    # 테스트 (API 키 필요)
    print("RationalTradingAI 모듈 로드 완료")
    print("사용법: RationalTradingAI(api_key, capital)")

    # 빠른 EV 체크 테스트
    result = quick_ev_check(
        entry=100_000_000,
        stop=97_000_000,
        target=109_000_000
    )
    print(f"\n빠른 EV 체크 결과: {result}")
