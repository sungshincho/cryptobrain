"""
CryptoBrain V3 - 이성적 트레이더 UI

기대값 기반 거래 검증기 + AI 상담
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from cryptobrain_v2.config.settings import (
    DB_PATH,
    DEFAULT_COINS,
    format_krw,
    format_percent,
)
from cryptobrain_v2.database.db_manager import DBManager
from cryptobrain_v2.core.data_fetcher import DataFetcher
from cryptobrain_v2.core.decision_engine import (
    ExpectedValueCalculator,
    TradeSetup,
    MarketAnalyzer,
    EmotionFilter,
)


def get_api_key() -> str:
    """API 키 가져오기"""
    api_key = st.secrets.get("GOOGLE_API_KEY", None)
    if not api_key:
        api_key = st.session_state.get("api_key")
    return api_key


def render_rational_trader_page():
    """이성적 트레이더 페이지"""
    st.header("🧠 이성적 트레이더 (V3)")
    st.caption("수학적 기대값에 기반한 냉철한 투자 판단")

    # 탭 구성
    tab_validator, tab_market, tab_chat = st.tabs([
        "🔍 거래 검증기",
        "📊 시장 분석",
        "💬 AI 상담"
    ])

    with tab_validator:
        render_trade_validator()

    with tab_market:
        render_market_analysis()

    with tab_chat:
        render_ai_chat()


def render_trade_validator():
    """거래 검증기 탭"""
    st.subheader("🔍 거래 기대값 검증기")
    st.markdown("""
    거래 전 **기대값(EV)** 과 **손익비(R:R)** 를 계산하여 수익성을 검증합니다.

    **기준:**
    - ✅ 기대값 > 0.5%
    - ✅ 손익비 > 1.5
    - ✅ 추정 승률 > 40%
    """)

    st.divider()

    # 입력 폼
    col1, col2 = st.columns(2)

    with col1:
        # 코인 선택
        db = DBManager(str(DB_PATH))
        profile = db.get_profile()
        coins = profile.preferred_coins if profile else ["BTC", "ETH", "XRP"]
        symbols = [f"{c}/KRW" for c in coins]

        symbol = st.selectbox("종목", symbols, index=0)

        # 방향
        side = st.radio("방향", ["매수 (Long)", "매도 (Short)"], horizontal=True)
        side_value = "long" if "Long" in side else "short"

    with col2:
        # 현재가 조회
        fetcher = DataFetcher()
        try:
            current_price = fetcher.get_current_price(symbol)
        except:
            current_price = 100_000_000  # 기본값

        st.metric("현재가", format_krw(current_price))

    st.divider()

    # 가격 입력
    col1, col2, col3 = st.columns(3)

    with col1:
        entry_price = st.number_input(
            "진입가 (원)",
            min_value=0,
            value=int(current_price),
            step=int(current_price * 0.01),
            help="매수/매도 예정 가격"
        )

    with col2:
        # 기본 손절가 계산 (2% 손실)
        default_stop = int(entry_price * 0.98) if side_value == "long" else int(entry_price * 1.02)
        stop_loss = st.number_input(
            "손절가 (원)",
            min_value=0,
            value=default_stop,
            step=int(current_price * 0.005),
            help="손절 예정 가격"
        )

    with col3:
        # 기본 목표가 계산 (6% 수익, 1:3 손익비)
        default_target = int(entry_price * 1.06) if side_value == "long" else int(entry_price * 0.94)
        take_profit = st.number_input(
            "목표가 (원)",
            min_value=0,
            value=default_target,
            step=int(current_price * 0.01),
            help="익절 예정 가격"
        )

    # 분석 실행
    if st.button("🔍 기대값 분석", type="primary", use_container_width=True):
        if entry_price > 0 and stop_loss > 0 and take_profit > 0:
            analyze_trade_setup(symbol, side_value, entry_price, stop_loss, take_profit)
        else:
            st.error("모든 가격을 입력해주세요")


def analyze_trade_setup(symbol: str, side: str, entry: float, stop: float, target: float):
    """거래 셋업 분석 실행"""

    # 시장 데이터 조회
    fetcher = DataFetcher()
    try:
        df = fetcher.get_ohlcv(symbol, "1h", 100)
    except:
        df = pd.DataFrame()

    # 시장 분석
    analyzer = MarketAnalyzer()
    if len(df) > 0:
        context = analyzer.analyze(df, symbol)
        context_dict = context.to_dict()
    else:
        context = None
        context_dict = {}

    # EV 계산
    calc = ExpectedValueCalculator()
    setup = TradeSetup(
        symbol=symbol,
        side=side,
        entry_price=entry,
        stop_loss=stop,
        take_profit=target
    )
    result = calc.analyze(setup, context_dict)

    st.divider()

    # 결과 표시
    rec = result.recommendation.value
    if rec == "enter":
        st.success("## ✅ 진입 가능")
    elif rec == "skip":
        st.error("## ❌ 진입 금지")
    else:
        st.warning("## ⏸️ 조건 대기")

    # 핵심 지표
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        ev_color = "green" if result.expected_value > 0 else "red"
        st.metric(
            "기대값",
            f"{result.expected_value:+.2f}%",
            delta="양수" if result.expected_value > 0 else "음수"
        )

    with col2:
        rr_status = "양호" if result.risk_reward_ratio >= 1.5 else "불리"
        st.metric(
            "손익비",
            f"1:{result.risk_reward_ratio:.1f}",
            delta=rr_status
        )

    with col3:
        st.metric(
            "추정 승률",
            f"{result.win_probability * 100:.0f}%",
            delta="높음" if result.win_probability > 0.5 else "보통"
        )

    with col4:
        confidence_map = {"high": "높음", "medium": "보통", "low": "낮음"}
        st.metric(
            "신뢰도",
            confidence_map.get(result.confidence.value, "보통")
        )

    # 리스크/리워드 계산
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📉 리스크")
        st.write(f"- 손실률: **{result.risk_percent:.2f}%**")
        st.write(f"- 진입가 → 손절가: {format_krw(entry)} → {format_krw(stop)}")

    with col2:
        st.markdown("### 📈 리워드")
        st.write(f"- 수익률: **{result.reward_percent:.2f}%**")
        st.write(f"- 진입가 → 목표가: {format_krw(entry)} → {format_krw(target)}")

    # 포지션 크기 권장
    st.divider()
    st.markdown("### 💰 권장 포지션")

    db = DBManager(str(DB_PATH))
    profile = db.get_profile()
    capital = profile.total_capital if profile else 1_000_000

    recommended_size = capital * result.kelly_fraction
    risk_amount = capital * 0.02

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("권장 투자금", format_krw(recommended_size))

    with col2:
        st.metric("최대 손실", format_krw(risk_amount))

    with col3:
        st.metric("자본 대비", f"{result.optimal_position_pct:.1f}%")

    # 판단 근거
    st.divider()
    st.markdown("### 📋 판단 근거")
    for reason in result.reasoning:
        st.markdown(f"- {reason}")

    # 시장 컨텍스트 (있으면)
    if context:
        with st.expander("📊 시장 분석 상세"):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**시장 국면:** {context.regime.value}")
                st.write(f"**추세:** {context.trend_direction} ({context.trend_strength.value})")
                st.write(f"**RSI:** {context.rsi:.1f} ({context.rsi_signal})")
                st.write(f"**MACD:** {context.macd_signal}")

            with col2:
                st.write(f"**MA 정렬:** {context.ma_alignment}")
                st.write(f"**변동성:** {context.volatility_regime}")
                st.write(f"**매수 점수:** {context.bullish_score:.0f}/100")
                st.write(f"**매도 점수:** {context.bearish_score:.0f}/100")


def render_market_analysis():
    """시장 분석 탭"""
    st.subheader("📊 실시간 시장 분석")

    # 코인 선택
    db = DBManager(str(DB_PATH))
    profile = db.get_profile()
    coins = profile.preferred_coins if profile else ["BTC", "ETH", "XRP"]

    col1, col2 = st.columns([3, 1])

    with col1:
        selected_coins = st.multiselect(
            "분석할 코인",
            options=coins,
            default=coins[:3]
        )

    with col2:
        if st.button("🔄 새로고침"):
            st.rerun()

    if not selected_coins:
        st.info("분석할 코인을 선택해주세요")
        return

    # 시장 분석 실행
    fetcher = DataFetcher()
    analyzer = MarketAnalyzer()
    calc = ExpectedValueCalculator()

    for coin in selected_coins:
        symbol = f"{coin}/KRW"

        with st.expander(f"**{coin}**", expanded=True):
            try:
                df = fetcher.get_ohlcv(symbol, "1h", 100)
                if len(df) == 0:
                    st.warning("데이터를 가져올 수 없습니다")
                    continue

                context = analyzer.analyze(df, symbol)
                current_price = df.iloc[-1]['close']

                # 요약
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("현재가", format_krw(current_price))

                with col2:
                    regime_emoji = {
                        "강세 상승": "🚀",
                        "상승": "📈",
                        "횡보": "➡️",
                        "하락": "📉",
                        "강세 하락": "💥",
                        "고변동성": "⚡",
                    }
                    emoji = regime_emoji.get(context.regime.value, "")
                    st.metric("시장 국면", f"{emoji} {context.regime.value}")

                with col3:
                    rsi_color = "🟢" if context.rsi < 40 else "🔴" if context.rsi > 60 else "🟡"
                    st.metric("RSI", f"{rsi_color} {context.rsi:.1f}")

                with col4:
                    st.metric("추천 전략", context.recommended_strategy.upper())

                # 점수 바
                st.markdown("**매수/매도 유리도**")
                col1, col2 = st.columns(2)

                with col1:
                    st.progress(int(context.bullish_score), text=f"매수 {context.bullish_score:.0f}")

                with col2:
                    st.progress(int(context.bearish_score), text=f"매도 {context.bearish_score:.0f}")

                # 지지/저항
                st.markdown(f"""
                **지지선:** {format_krw(context.nearest_support)} ({context.distance_to_support_pct:.1f}% 아래)
                **저항선:** {format_krw(context.nearest_resistance)} ({context.distance_to_resistance_pct:.1f}% 위)
                """)

                # 분석 근거
                st.markdown("**분석:**")
                for r in context.reasoning:
                    st.write(f"- {r}")

            except Exception as e:
                st.error(f"분석 오류: {str(e)}")


def render_ai_chat():
    """AI 상담 탭"""
    st.subheader("💬 이성적 AI 상담")

    api_key = get_api_key()
    if not api_key:
        st.warning("AI 상담을 위해 사이드바에서 API 키를 입력해주세요")
        return

    st.markdown("""
    > 이 AI는 **기대값 기반**으로 판단합니다.
    > 감정적 요청(FOMO, 공포, 복수매매)은 **거절**될 수 있습니다.
    """)

    # 세션 초기화
    if "rational_messages" not in st.session_state:
        st.session_state.rational_messages = [
            {
                "role": "assistant",
                "content": """안녕하세요. 저는 **이성적 트레이딩 AI**입니다.

저는 오직 **수학적 기대값**과 **확률**에 기반해서 판단합니다.

**할 수 있는 것:**
- 거래 기대값 분석
- 시장 상황 분석
- 적정 포지션 크기 계산
- 나쁜 습관 교정

**하지 않는 것:**
- 가격 예측 ("얼마까지 갈까요?")
- 감정에 동조 ("지금 사야할 것 같아요")
- 모호한 조언 ("지켜보세요")

무엇을 분석해드릴까요?"""
            }
        ]

    # 채팅 히스토리 표시
    for msg in st.session_state.rational_messages:
        st.chat_message(msg["role"]).write(msg["content"])

    # 사용자 입력
    if prompt := st.chat_input("질문을 입력하세요 (예: 비트코인 지금 사도 될까?)"):
        st.session_state.rational_messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        # 감정 필터 먼저 적용
        emotion_filter = EmotionFilter()
        emotion_result = emotion_filter.analyze_request(prompt)

        with st.chat_message("assistant"):
            if not emotion_result.is_rational:
                # 감정적 요청 감지
                response = f"""
⚠️ **감정적 거래 경고**

감지된 감정: {', '.join(emotion_result.detected_emotions)}
감정 점수: {emotion_result.emotion_score * 100:.0f}/100

{chr(10).join(emotion_result.warnings)}

---

{emotion_result.alternative_advice}

---

{'🛑 **지금은 거래를 쉬세요.** 감정적 상태에서의 거래는 손실로 이어집니다.' if emotion_result.should_block else '⚠️ 냉정하게 기대값을 계산한 후 결정하세요.'}
"""
                st.write(response)
                st.session_state.rational_messages.append({"role": "assistant", "content": response})

            else:
                # AI 응답 생성
                with st.spinner("분석 중..."):
                    try:
                        from cryptobrain_v2.core.rational_ai import RationalTradingAI

                        db = DBManager(str(DB_PATH))
                        profile = db.get_profile()
                        capital = profile.total_capital if profile else 1_000_000

                        ai = RationalTradingAI(api_key, capital)

                        # 기본 코인의 OHLCV 데이터 조회
                        fetcher = DataFetcher()
                        symbol = "BTC/KRW"
                        try:
                            df = fetcher.get_ohlcv(symbol, "1h", 100)
                            price = fetcher.get_current_price(symbol)
                            market_data = {
                                "symbol": symbol,
                                "price": price,
                                "recent_move": {"change_24h": 0}
                            }
                        except:
                            df = pd.DataFrame()
                            market_data = {}

                        response = ai.process_request(
                            prompt,
                            market_data=market_data,
                            ohlcv_data=df
                        )

                        st.write(response)
                        st.session_state.rational_messages.append({"role": "assistant", "content": response})

                    except Exception as e:
                        error_msg = f"AI 응답 생성 오류: {str(e)}"
                        st.error(error_msg)
                        st.session_state.rational_messages.append({"role": "assistant", "content": error_msg})


if __name__ == "__main__":
    st.set_page_config(page_title="이성적 트레이더", layout="wide")
    render_rational_trader_page()
