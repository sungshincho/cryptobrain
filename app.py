"""
CryptoBrain V2 - 초개인화 AI 암호화폐 투자 어시스턴트
메인 Streamlit 애플리케이션
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os
from pathlib import Path

# 경로 설정 - cryptobrain_v2 모듈 import를 위해
sys.path.insert(0, str(Path(__file__).parent))

from cryptobrain_v2.config.settings import (
    PAGE_CONFIG,
    DEFAULT_COINS,
    format_krw,
    format_percent,
    INVESTMENT_GOALS,
    INVESTMENT_HORIZONS,
    RISK_TOLERANCES,
    VOLATILITY_PREFERENCES,
    TRADING_STYLES,
    TRADING_FREQUENCIES,
    TRADING_SESSIONS,
    SKILL_LEVELS,
    COMMON_MISTAKES,
    MARKET_CONDITIONS,
    TRIGGER_REASONS,
    EMOTIONAL_STATES,
)
from cryptobrain_v2.database.db_manager import DBManager
from cryptobrain_v2.database.models import InvestorProfile, Position, TradeHistory
from cryptobrain_v2.core.data_fetcher import DataFetcher
from cryptobrain_v2.core.technical_analyzer import TechnicalAnalyzer
from cryptobrain_v2.core.position_sizer import PositionSizer
from cryptobrain_v2.core.ai_engine import AIEngine

# 페이지 설정
st.set_page_config(**PAGE_CONFIG)

# DB 경로 설정 (Streamlit Cloud 호환)
DB_FILE = os.path.join(os.path.dirname(__file__), "cryptobrain.db")


def init_session_state():
    """세션 상태 초기화"""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "안녕하세요! CryptoBrain V2입니다. 무엇을 도와드릴까요?"}
        ]
    if "api_key" not in st.session_state:
        st.session_state.api_key = None


def get_api_key() -> str:
    """API 키 가져오기"""
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY", None)
    except Exception:
        api_key = None

    if not api_key:
        api_key = st.session_state.get("api_key")

    return api_key


def render_sidebar():
    """사이드바 렌더링"""
    with st.sidebar:
        st.title("🧠 CryptoBrain V2")
        st.caption("초개인화 AI 투자 어시스턴트")

        st.divider()

        # API 키 입력
        api_key = get_api_key()
        if not api_key:
            st.warning("Google AI API 키를 입력해주세요")
            new_key = st.text_input("API Key", type="password")
            if new_key:
                st.session_state.api_key = new_key
                st.rerun()
        else:
            st.success("API 연결됨")

        st.divider()

        # 프로필 요약
        db = DBManager(DB_FILE)
        profile = db.get_profile()

        if profile:
            st.markdown("**내 프로필**")
            st.write(f"자본금: {format_krw(profile.total_capital)}")
            st.write(f"리스크: {profile.risk_per_trade * 100:.1f}%/회")
            st.write(f"스타일: {profile.trading_style}")
        else:
            st.info("프로필을 설정해주세요")

        st.divider()

        # 포트폴리오 요약
        portfolio = db.get_portfolio_summary()
        if portfolio.positions:
            st.markdown("**내 포트폴리오**")
            st.write(f"평가금: {format_krw(portfolio.total_value)}")
            st.write(f"손익: {format_percent(portfolio.total_pnl_pct, True)}")

        st.divider()

        # 새로고침 버튼
        if st.button("🔄 데이터 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()


def render_dashboard():
    """대시보드 탭 렌더링"""
    st.header("📊 대시보드")

    db = DBManager(DB_FILE)
    profile = db.get_profile()

    # 시장 데이터 로드
    with st.spinner("시장 데이터를 불러오는 중..."):
        fetcher = DataFetcher()
        coins = profile.preferred_coins if profile else ["BTC", "ETH", "XRP", "SOL", "DOGE"]
        symbols = [f"{c}/KRW" for c in coins]
        market_summary = fetcher.get_market_summary(symbols)

    # 시장 개요
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("관심 코인 수", f"{market_summary['total_coins']}개")

    with col2:
        st.metric("상승", f"{market_summary['bullish_count']}개", delta="📈")

    with col3:
        st.metric("하락", f"{market_summary['bearish_count']}개", delta="📉", delta_color="inverse")

    with col4:
        sentiment_text = {
            "very_bullish": "매우 낙관",
            "bullish": "낙관",
            "neutral": "중립",
            "bearish": "비관",
            "very_bearish": "매우 비관"
        }
        st.metric("시장 심리", sentiment_text.get(market_summary['market_sentiment'], "중립"))

    st.divider()

    # 실시간 시세
    st.subheader("📈 실시간 시세")

    if market_summary.get("data"):
        cols = st.columns(3)

        for i, (symbol, data) in enumerate(market_summary["data"].items()):
            with cols[i % 3]:
                coin = symbol.split("/")[0]
                trend_emoji = "📈" if data["trend"] == "bullish" else "📉"
                change_color = "green" if data.get("change", 0) >= 0 else "red"

                st.markdown(f"""
                **{coin}** {trend_emoji}
                - 가격: {format_krw(data['price'])}
                - RSI: {data['rsi']:.1f}
                - :{change_color}[{data.get('change', 0):+.2f}%]
                """)

        if market_summary.get("oversold_coins"):
            st.info(f"📉 과매도 구간: {', '.join([s.split('/')[0] for s in market_summary['oversold_coins']])}")

        if market_summary.get("overbought_coins"):
            st.warning(f"📈 과매수 구간: {', '.join([s.split('/')[0] for s in market_summary['overbought_coins']])}")

    st.divider()

    # 빠른 포지션 계산기
    st.subheader("🧮 포지션 계산기")

    if profile:
        col1, col2, col3 = st.columns(3)

        with col1:
            entry_price = st.number_input("진입가 (KRW)", min_value=0, value=0, step=10000)

        with col2:
            stop_loss = st.number_input("손절가 (KRW)", min_value=0, value=0, step=10000)

        with col3:
            if entry_price > 0 and stop_loss > 0 and entry_price != stop_loss:
                sizer = PositionSizer(profile.total_capital, profile.risk_per_trade)
                result = sizer.calculate_position(entry_price, stop_loss)

                st.metric("추천 매수금액", format_krw(result.position_value))
                st.caption(f"손절 시 손실: {format_krw(result.risk_amount)}")
                st.caption(f"목표가 (1:2): {format_krw(result.target_1to2)}")
    else:
        st.info("포지션 계산을 위해 프로필을 먼저 설정해주세요")


def render_ai_analysis():
    """AI 분석 탭 렌더링"""
    st.header("🤖 AI 분석")

    api_key = get_api_key()
    if not api_key:
        st.warning("AI 분석을 위해 사이드바에서 API 키를 입력해주세요")
        return

    db = DBManager(DB_FILE)
    profile = db.get_profile()
    portfolio = db.get_portfolio_summary()
    trade_stats = db.get_trade_stats()

    engine = AIEngine(
        api_key=api_key,
        profile=profile,
        portfolio=portfolio,
        trade_stats=trade_stats
    )

    fetcher = DataFetcher()
    coins = profile.preferred_coins if profile else ["BTC", "ETH"]
    symbols = [f"{c}/KRW" for c in coins]
    market_data = fetcher.get_all_watched_coins(symbols)

    analysis_type = st.radio(
        "분석 유형",
        ["전체 시장 분석", "종목별 상세 분석", "AI 대화"],
        horizontal=True
    )

    if analysis_type == "전체 시장 분석":
        if st.button("🚀 AI 시장 분석 실행", type="primary"):
            with st.spinner("AI가 시장을 분석하고 있습니다..."):
                result = engine.analyze_market(market_data)
                st.markdown(result)

                if profile:
                    warning = engine.get_personalized_warning("buy", "", None)
                    if warning:
                        st.warning(warning)

    elif analysis_type == "종목별 상세 분석":
        selected_symbol = st.selectbox("분석할 종목", options=symbols)

        if st.button("📊 상세 분석 실행", type="primary"):
            with st.spinner(f"{selected_symbol} 분석 중..."):
                df = fetcher.get_ohlcv(selected_symbol, "1h", 100)
                if not df.empty:
                    analyzer = TechnicalAnalyzer(df)
                    signals = analyzer.get_signals()

                    symbol_data = market_data.get(selected_symbol, {})
                    result = engine.analyze_symbol(selected_symbol, symbol_data, signals)

                    st.markdown(result)

                    with st.expander("📈 기술적 분석 상세"):
                        st.markdown(analyzer.get_analysis_text())

    else:
        st.markdown("### 💬 AI 상담")

        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).write(msg["content"])

        context_lines = []
        for sym, data in market_data.items():
            context_lines.append(f"- {sym}: {data['price']:,.0f}원 (RSI: {data['rsi']:.1f})")
        market_context = "\n".join(context_lines)

        if prompt := st.chat_input("질문을 입력하세요"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("생각 중..."):
                    response = engine.chat(prompt, market_context)
                    st.write(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})


def render_profile_page():
    """프로필 설정 페이지"""
    st.header("⚙️ 투자 프로필 설정")
    st.caption("AI가 당신에게 맞는 조언을 하기 위해 필요한 정보입니다")

    db = DBManager(DB_FILE)
    existing_profile = db.get_profile()

    if existing_profile:
        profile = existing_profile
        st.success("기존 프로필을 불러왔습니다")
    else:
        profile = InvestorProfile()
        st.info("새 프로필을 설정해주세요")

    tab1, tab2, tab3, tab4 = st.tabs([
        "💰 자본 & 리스크",
        "📊 거래 스타일",
        "🎓 경험 수준",
        "⚠️ 과거 실수"
    ])

    with tab1:
        st.subheader("자본금 및 리스크 설정")

        col1, col2 = st.columns(2)

        with col1:
            total_capital = st.number_input(
                "총 투자 자본금 (KRW)",
                min_value=100000,
                max_value=1000000000,
                value=profile.total_capital,
                step=100000
            )

            monthly_income = st.number_input(
                "월 수입 (KRW)",
                min_value=0,
                max_value=100000000,
                value=profile.monthly_income,
                step=100000
            )

        with col2:
            max_loss_tolerance = st.slider(
                "최대 감내 가능 손실률 (%)",
                min_value=5, max_value=50,
                value=int(profile.max_loss_tolerance * 100),
                step=5
            ) / 100

            risk_per_trade = st.slider(
                "1회 거래당 리스크 (%)",
                min_value=0.5, max_value=5.0,
                value=profile.risk_per_trade * 100,
                step=0.5
            ) / 100

        st.divider()

        col3, col4 = st.columns(2)

        with col3:
            investment_goal = st.selectbox(
                "투자 목표",
                options=list(INVESTMENT_GOALS.keys()),
                index=list(INVESTMENT_GOALS.keys()).index(profile.investment_goal)
                if profile.investment_goal in INVESTMENT_GOALS else 1
            )

        with col4:
            investment_horizon = st.selectbox(
                "투자 기간",
                options=list(INVESTMENT_HORIZONS.keys()),
                index=list(INVESTMENT_HORIZONS.keys()).index(profile.investment_horizon)
                if profile.investment_horizon in INVESTMENT_HORIZONS else 1
            )

        col5, col6 = st.columns(2)

        with col5:
            risk_tolerance = st.selectbox(
                "리스크 성향",
                options=list(RISK_TOLERANCES.keys()),
                index=list(RISK_TOLERANCES.keys()).index(profile.risk_tolerance)
                if profile.risk_tolerance in RISK_TOLERANCES else 1,
                format_func=lambda x: f"{x} - {RISK_TOLERANCES[x].split(' - ')[1]}"
            )

        with col6:
            preferred_volatility = st.selectbox(
                "선호 변동성",
                options=list(VOLATILITY_PREFERENCES.keys()),
                index=list(VOLATILITY_PREFERENCES.keys()).index(profile.preferred_volatility)
                if profile.preferred_volatility in VOLATILITY_PREFERENCES else 1,
                format_func=lambda x: f"{x} - {VOLATILITY_PREFERENCES[x].split(' - ')[1]}"
            )

        leverage_allowed = st.checkbox("레버리지 사용 허용", value=profile.leverage_allowed)

    with tab2:
        st.subheader("거래 스타일 설정")

        col1, col2 = st.columns(2)

        with col1:
            trading_style = st.selectbox(
                "트레이딩 스타일",
                options=list(TRADING_STYLES.keys()),
                index=list(TRADING_STYLES.keys()).index(profile.trading_style)
                if profile.trading_style in TRADING_STYLES else 1,
                format_func=lambda x: f"{x} - {TRADING_STYLES[x].split(' - ')[1]}"
            )

            trading_frequency = st.selectbox(
                "거래 빈도",
                options=list(TRADING_FREQUENCIES.keys()),
                index=list(TRADING_FREQUENCIES.keys()).index(profile.trading_frequency)
                if profile.trading_frequency in TRADING_FREQUENCIES else 1,
                format_func=lambda x: f"{x} - {TRADING_FREQUENCIES[x].split(' - ')[1]}"
            )

        with col2:
            preferred_session = st.selectbox(
                "선호 거래 세션",
                options=list(TRADING_SESSIONS.keys()),
                index=list(TRADING_SESSIONS.keys()).index(profile.preferred_session)
                if profile.preferred_session in TRADING_SESSIONS else 0,
                format_func=lambda x: TRADING_SESSIONS[x]
            )

            available_time = st.slider(
                "하루 차트 분석 가능 시간 (분)",
                min_value=10, max_value=480,
                value=profile.available_time_per_day,
                step=10
            )

        st.divider()
        st.subheader("활성 거래 시간")

        col3, col4 = st.columns(2)

        with col3:
            active_hours_start = st.text_input("시작 시간 (HH:MM)", value=profile.active_hours_start)

        with col4:
            active_hours_end = st.text_input("종료 시간 (HH:MM)", value=profile.active_hours_end)

        st.divider()
        st.subheader("관심 코인 설정")

        available_coins = ["BTC", "ETH", "XRP", "SOL", "DOGE", "ADA", "AVAX", "MATIC", "LINK", "DOT"]

        preferred_coins = st.multiselect(
            "관심 코인 선택",
            options=available_coins,
            default=[c for c in profile.preferred_coins if c in available_coins]
        )

    with tab3:
        st.subheader("투자 경험 및 기술 수준")

        col1, col2 = st.columns(2)

        with col1:
            experience_years = st.number_input(
                "투자 경력 (년)",
                min_value=0.0, max_value=30.0,
                value=profile.experience_years,
                step=0.5
            )

        with col2:
            technical_skill = st.selectbox(
                "기술적 분석 수준",
                options=list(SKILL_LEVELS.keys()),
                index=list(SKILL_LEVELS.keys()).index(profile.technical_analysis_skill)
                if profile.technical_analysis_skill in SKILL_LEVELS else 0,
                format_func=lambda x: f"{x} - {SKILL_LEVELS[x].split(' - ')[1]}"
            )

    with tab4:
        st.subheader("과거 투자 실수 (자기 인식)")
        st.caption("솔직하게 체크하면 AI가 해당 실수를 반복하지 않도록 경고해줍니다")

        past_mistakes = []

        col1, col2 = st.columns(2)

        for i, mistake in enumerate(COMMON_MISTAKES):
            col = col1 if i < len(COMMON_MISTAKES) // 2 else col2
            with col:
                if st.checkbox(mistake, value=mistake in profile.past_major_mistakes, key=f"mistake_{i}"):
                    past_mistakes.append(mistake)

        if past_mistakes:
            st.warning(f"인식한 약점: {', '.join(past_mistakes)}")

    st.divider()

    if st.button("💾 프로필 저장", type="primary", use_container_width=True):
        new_profile = InvestorProfile(
            total_capital=total_capital,
            monthly_income=monthly_income,
            investment_goal=investment_goal,
            investment_horizon=investment_horizon,
            max_loss_tolerance=max_loss_tolerance,
            risk_per_trade=risk_per_trade,
            risk_tolerance=risk_tolerance,
            preferred_volatility=preferred_volatility,
            leverage_allowed=leverage_allowed,
            trading_style=trading_style,
            trading_frequency=trading_frequency,
            preferred_session=preferred_session,
            available_time_per_day=available_time,
            active_hours_start=active_hours_start,
            active_hours_end=active_hours_end,
            experience_years=experience_years,
            technical_analysis_skill=technical_skill,
            past_major_mistakes=past_mistakes,
            preferred_coins=preferred_coins,
        )

        try:
            db.save_profile(new_profile)
            st.success("프로필이 저장되었습니다!")
            st.balloons()
        except Exception as e:
            st.error(f"저장 중 오류가 발생했습니다: {e}")


def render_portfolio_page():
    """포트폴리오 관리 페이지"""
    st.header("💼 포트폴리오 관리")

    db = DBManager(DB_FILE)

    tab1, tab2, tab3 = st.tabs(["📊 현황", "➕ 포지션 추가", "💵 현금 관리"])

    with tab1:
        summary = db.get_portfolio_summary()
        cash = db.get_cash_balance()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("총 자산", format_krw(summary.total_value + cash))
        with col2:
            st.metric("투자금", format_krw(summary.total_invested))
        with col3:
            pnl_delta = f"{summary.total_pnl_pct:+.2f}%" if summary.total_invested > 0 else None
            st.metric("평가손익", format_krw(summary.total_pnl), delta=pnl_delta)
        with col4:
            st.metric("현금", format_krw(cash))

        if summary.positions:
            st.divider()
            st.subheader("보유 종목")

            for pos in summary.positions:
                coin = pos.symbol.split("/")[0]
                pnl_color = "green" if pos.unrealized_pnl >= 0 else "red"

                with st.expander(f"{coin} - {format_krw(pos.current_value)}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"수량: {pos.quantity:.8f}")
                        st.write(f"평균단가: {format_krw(pos.avg_entry_price)}")
                    with col2:
                        st.write(f"현재가: {format_krw(pos.current_price)}")
                        st.markdown(f"손익: :{pnl_color}[{format_krw(pos.unrealized_pnl)} ({pos.unrealized_pnl_pct:+.2f}%)]")

    with tab2:
        st.subheader("새 포지션 추가")

        with st.form("add_position"):
            col1, col2 = st.columns(2)

            with col1:
                coin_options = ["BTC", "ETH", "XRP", "SOL", "DOGE", "기타"]
                selected_coin = st.selectbox("코인", options=coin_options)

                if selected_coin == "기타":
                    custom_coin = st.text_input("코인 심볼")
                    symbol = f"{custom_coin.upper()}/KRW" if custom_coin else ""
                else:
                    symbol = f"{selected_coin}/KRW"

                quantity = st.number_input("수량", min_value=0.0, format="%.8f")

            with col2:
                avg_price = st.number_input("평균 매수가 (KRW)", min_value=0, step=1000)
                current_price = st.number_input("현재가 (KRW)", min_value=0, step=1000)

            if st.form_submit_button("포지션 추가", type="primary"):
                if symbol and quantity > 0 and avg_price > 0:
                    position = Position(
                        symbol=symbol,
                        quantity=quantity,
                        avg_entry_price=avg_price,
                        current_price=current_price if current_price > 0 else avg_price,
                        first_buy_date=datetime.now(),
                        last_buy_date=datetime.now()
                    )
                    db.save_position(position)
                    st.success(f"{symbol} 포지션이 추가되었습니다!")
                    st.rerun()
                else:
                    st.error("모든 필드를 올바르게 입력해주세요")

    with tab3:
        current_cash = db.get_cash_balance()
        st.metric("현재 현금 잔고", format_krw(current_cash))

        new_cash = st.number_input("새 현금 잔고 (KRW)", min_value=0, value=int(current_cash), step=100000)

        if st.button("현금 저장", type="primary"):
            db.set_cash_balance(new_cash)
            st.success("현금 잔고가 업데이트되었습니다!")
            st.rerun()


def render_journal_page():
    """매매일지 페이지"""
    st.header("📝 매매일지")

    db = DBManager(DB_FILE)

    tab1, tab2, tab3 = st.tabs(["📊 통계", "➕ 거래 추가", "📋 기록"])

    with tab1:
        stats = db.get_trade_stats()

        if stats["total_trades"] == 0:
            st.info("아직 기록된 거래가 없습니다")
        else:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("총 거래", f"{stats['total_trades']}회")
            with col2:
                st.metric("승률", f"{stats.get('win_rate', 0):.1f}%")
            with col3:
                st.metric("손익비", f"{stats.get('profit_factor', 0):.2f}")
            with col4:
                total_pnl = stats.get('total_profit', 0) - stats.get('total_loss', 0)
                st.metric("순손익", format_krw(total_pnl))

            st.divider()

            trigger_stats = db.get_trades_by_trigger()
            if trigger_stats:
                st.subheader("매매 이유별 성과")
                for reason, data in trigger_stats.items():
                    st.write(f"- **{reason}**: 승률 {data['win_rate']:.1f}%, 평균 수익률 {data['avg_pnl_pct']:.2f}%")

    with tab2:
        st.subheader("새 거래 기록")

        side = st.radio("거래 유형", ["매수", "매도"], horizontal=True)
        trade_side = "buy" if side == "매수" else "sell"

        with st.form("add_trade"):
            col1, col2 = st.columns(2)

            with col1:
                coin_options = ["BTC", "ETH", "XRP", "SOL", "DOGE"]
                selected_coin = st.selectbox("코인", options=coin_options)
                symbol = f"{selected_coin}/KRW"

                quantity = st.number_input("수량", min_value=0.0, format="%.8f")
                price = st.number_input("거래 가격 (KRW)", min_value=0, step=1000)

            with col2:
                market_condition = st.selectbox(
                    "시장 상황",
                    options=list(MARKET_CONDITIONS.keys()),
                    format_func=lambda x: MARKET_CONDITIONS[x]
                )

                trigger_reason = st.selectbox("매매 이유", options=list(TRIGGER_REASONS.keys()))
                emotional_state = st.selectbox("감정 상태", options=list(EMOTIONAL_STATES.keys()))

            pnl = None
            pnl_pct = None

            if trade_side == "sell":
                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    pnl = st.number_input("손익 금액 (KRW)", value=0, step=10000)
                with col2:
                    pnl_pct = st.number_input("손익률 (%)", value=0.0, step=0.5)

            notes = st.text_area("메모")

            if st.form_submit_button("거래 기록 추가", type="primary"):
                if quantity > 0 and price > 0:
                    trade = TradeHistory(
                        symbol=symbol,
                        side=trade_side,
                        quantity=quantity,
                        price=price,
                        timestamp=datetime.now(),
                        market_condition=market_condition,
                        trigger_reason=trigger_reason,
                        emotional_state=emotional_state,
                        pnl=pnl if trade_side == "sell" else None,
                        pnl_pct=pnl_pct if trade_side == "sell" else None,
                        notes=notes
                    )
                    db.add_trade(trade)
                    st.success("거래가 기록되었습니다!")
                    st.balloons()
                else:
                    st.error("수량과 가격을 입력해주세요")

    with tab3:
        trades = db.get_trades(limit=20)

        if not trades:
            st.info("기록된 거래가 없습니다")
        else:
            for trade in trades:
                emoji = "🟢" if trade.side == "buy" else "🔴"
                date_str = trade.timestamp.strftime("%Y-%m-%d %H:%M") if trade.timestamp else ""

                with st.expander(f"{emoji} {trade.symbol} | {date_str}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"수량: {trade.quantity:.8f}")
                        st.write(f"가격: {format_krw(trade.price)}")
                        st.write(f"매매 이유: {trade.trigger_reason}")
                    with col2:
                        st.write(f"감정 상태: {trade.emotional_state}")
                        if trade.pnl is not None:
                            pnl_color = "green" if trade.pnl >= 0 else "red"
                            st.markdown(f"손익: :{pnl_color}[{format_krw(trade.pnl)}]")
                    if trade.notes:
                        st.write(f"메모: {trade.notes}")


def main():
    """메인 함수"""
    init_session_state()
    render_sidebar()

    tab_dashboard, tab_ai, tab_profile, tab_portfolio, tab_journal = st.tabs([
        "📊 대시보드",
        "🤖 AI 분석",
        "⚙️ 프로필",
        "💼 포트폴리오",
        "📝 매매일지"
    ])

    with tab_dashboard:
        render_dashboard()

    with tab_ai:
        render_ai_analysis()

    with tab_profile:
        render_profile_page()

    with tab_portfolio:
        render_portfolio_page()

    with tab_journal:
        render_journal_page()


if __name__ == "__main__":
    main()
