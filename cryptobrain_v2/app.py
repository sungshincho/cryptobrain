"""
CryptoBrain V2 - 초개인화 AI 암호화폐 투자 어시스턴트
메인 Streamlit 애플리케이션
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# 경로 설정
sys.path.insert(0, str(Path(__file__).parent.parent))

from cryptobrain_v2.config.settings import (
    PAGE_CONFIG,
    DB_PATH,
    DEFAULT_COINS,
    REFRESH_INTERVAL,
    format_krw,
    format_percent,
)
from cryptobrain_v2.database.db_manager import DBManager
from cryptobrain_v2.database.models import InvestorProfile
from cryptobrain_v2.core.data_fetcher import DataFetcher
from cryptobrain_v2.core.technical_analyzer import TechnicalAnalyzer
from cryptobrain_v2.core.position_sizer import PositionSizer
from cryptobrain_v2.core.ai_engine import AIEngine

# 페이지 설정
st.set_page_config(**PAGE_CONFIG)


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
    # Streamlit Secrets에서 먼저 확인
    api_key = st.secrets.get("GOOGLE_API_KEY", None)

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
        db = DBManager(str(DB_PATH))
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

    db = DBManager(str(DB_PATH))
    profile = db.get_profile()

    # 시장 데이터 로드
    with st.spinner("시장 데이터를 불러오는 중..."):
        fetcher = DataFetcher()
        coins = profile.preferred_coins if profile else [c.split("/")[0] for c in DEFAULT_COINS[:5]]
        symbols = [f"{c}/KRW" for c in coins]
        market_summary = fetcher.get_market_summary(symbols)

    # 시장 개요
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "관심 코인 수",
            f"{market_summary['total_coins']}개"
        )

    with col2:
        st.metric(
            "상승",
            f"{market_summary['bullish_count']}개",
            delta="📈"
        )

    with col3:
        st.metric(
            "하락",
            f"{market_summary['bearish_count']}개",
            delta="📉",
            delta_color="inverse"
        )

    with col4:
        sentiment_text = {
            "very_bullish": "매우 낙관",
            "bullish": "낙관",
            "neutral": "중립",
            "bearish": "비관",
            "very_bearish": "매우 비관"
        }
        st.metric(
            "시장 심리",
            sentiment_text.get(market_summary['market_sentiment'], "중립")
        )

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

        # 과매수/과매도 알림
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
            entry_price = st.number_input(
                "진입가 (KRW)",
                min_value=0,
                value=0,
                step=10000
            )

        with col2:
            stop_loss = st.number_input(
                "손절가 (KRW)",
                min_value=0,
                value=0,
                step=10000
            )

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

    db = DBManager(str(DB_PATH))
    profile = db.get_profile()
    portfolio = db.get_portfolio_summary()
    trade_stats = db.get_trade_stats()

    # AI 엔진 초기화
    engine = AIEngine(
        api_key=api_key,
        profile=profile,
        portfolio=portfolio,
        trade_stats=trade_stats
    )

    # 시장 데이터 로드
    fetcher = DataFetcher()
    coins = profile.preferred_coins if profile else ["BTC", "ETH"]
    symbols = [f"{c}/KRW" for c in coins]
    market_data = fetcher.get_all_watched_coins(symbols)

    # 분석 옵션
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

                # 개인 맞춤 경고
                if profile:
                    warning = engine.get_personalized_warning("buy", "", None)
                    if warning:
                        st.warning(warning)

    elif analysis_type == "종목별 상세 분석":
        selected_symbol = st.selectbox(
            "분석할 종목",
            options=symbols
        )

        if st.button("📊 상세 분석 실행", type="primary"):
            with st.spinner(f"{selected_symbol} 분석 중..."):
                # 기술적 분석
                df = fetcher.get_ohlcv(selected_symbol, "1h", 100)
                if not df.empty:
                    analyzer = TechnicalAnalyzer(df)
                    signals = analyzer.get_signals()

                    # AI 분석
                    symbol_data = market_data.get(selected_symbol, {})
                    result = engine.analyze_symbol(selected_symbol, symbol_data, signals)

                    st.markdown(result)

                    # 기술적 분석 결과
                    with st.expander("📈 기술적 분석 상세"):
                        st.markdown(analyzer.get_analysis_text())

    else:  # AI 대화
        st.markdown("### 💬 AI 상담")

        # 채팅 히스토리 표시
        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).write(msg["content"])

        # 시장 컨텍스트 생성
        context_lines = []
        for sym, data in market_data.items():
            context_lines.append(
                f"- {sym}: {data['price']:,.0f}원 (RSI: {data['rsi']:.1f})"
            )
        market_context = "\n".join(context_lines)

        # 사용자 입력
        if prompt := st.chat_input("질문을 입력하세요"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("생각 중..."):
                    response = engine.chat(prompt, market_context)
                    st.write(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})


def render_profile_page():
    """프로필 페이지 렌더링"""
    from cryptobrain_v2.ui.pages.profile import render_profile_page as render_profile
    render_profile()


def render_portfolio_page():
    """포트폴리오 페이지 렌더링"""
    from cryptobrain_v2.ui.pages.portfolio import render_portfolio_page as render_portfolio
    render_portfolio()


def render_journal_page():
    """매매일지 페이지 렌더링"""
    from cryptobrain_v2.ui.pages.journal import render_journal_page as render_journal
    render_journal()


def render_data_import_page():
    """데이터 임포트 페이지 렌더링"""
    from cryptobrain_v2.ui.pages.data_import import render_data_import_page as render_import
    render_import()


def main():
    """메인 함수"""
    init_session_state()
    render_sidebar()

    # 탭 구성
    tab_dashboard, tab_ai, tab_import, tab_profile, tab_portfolio, tab_journal = st.tabs([
        "📊 대시보드",
        "🤖 AI 분석",
        "📥 데이터 임포트",
        "⚙️ 프로필",
        "💼 포트폴리오",
        "📝 매매일지"
    ])

    with tab_dashboard:
        render_dashboard()

    with tab_ai:
        render_ai_analysis()

    with tab_import:
        render_data_import_page()

    with tab_profile:
        render_profile_page()

    with tab_portfolio:
        render_portfolio_page()

    with tab_journal:
        render_journal_page()


if __name__ == "__main__":
    main()
