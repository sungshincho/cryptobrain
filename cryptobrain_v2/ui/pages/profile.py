"""
CryptoBrain V2 - 투자 프로필 설정 페이지
"""
import streamlit as st
from ...database.models import InvestorProfile
from ...database.db_manager import DBManager
from ...config.settings import (
    INVESTMENT_GOALS,
    INVESTMENT_HORIZONS,
    RISK_TOLERANCES,
    VOLATILITY_PREFERENCES,
    TRADING_STYLES,
    TRADING_FREQUENCIES,
    TRADING_SESSIONS,
    SKILL_LEVELS,
    COMMON_MISTAKES,
    DB_PATH,
)


def render_profile_page():
    """투자 프로필 설정 페이지 렌더링"""
    st.header("⚙️ 투자 프로필 설정")
    st.caption("AI가 당신에게 맞는 조언을 하기 위해 필요한 정보입니다")

    # DB 연결
    db = DBManager(str(DB_PATH))

    # 기존 프로필 로드
    existing_profile = db.get_profile()
    if existing_profile:
        profile = existing_profile
        st.success("기존 프로필을 불러왔습니다")
    else:
        profile = InvestorProfile()
        st.info("새 프로필을 설정해주세요")

    # 탭으로 구분
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
                step=100000,
                help="암호화폐 투자에 사용할 총 자금"
            )

            monthly_income = st.number_input(
                "월 수입 (KRW)",
                min_value=0,
                max_value=100000000,
                value=profile.monthly_income,
                step=100000,
                help="추가 투자 여력 판단에 사용됩니다"
            )

        with col2:
            max_loss_tolerance = st.slider(
                "최대 감내 가능 손실률 (%)",
                min_value=5,
                max_value=50,
                value=int(profile.max_loss_tolerance * 100),
                step=5,
                help="전체 자본 대비 최대 얼마까지 손실을 감당할 수 있나요?"
            ) / 100

            risk_per_trade = st.slider(
                "1회 거래당 리스크 (%)",
                min_value=0.5,
                max_value=5.0,
                value=profile.risk_per_trade * 100,
                step=0.5,
                help="각 거래에서 감수할 최대 손실 비율 (권장: 1-2%)"
            ) / 100

        st.divider()

        col3, col4 = st.columns(2)

        with col3:
            investment_goal = st.selectbox(
                "투자 목표",
                options=list(INVESTMENT_GOALS.keys()),
                index=list(INVESTMENT_GOALS.keys()).index(profile.investment_goal)
                if profile.investment_goal in INVESTMENT_GOALS else 1,
                help=INVESTMENT_GOALS.get(profile.investment_goal, "")
            )

        with col4:
            investment_horizon = st.selectbox(
                "투자 기간",
                options=list(INVESTMENT_HORIZONS.keys()),
                index=list(INVESTMENT_HORIZONS.keys()).index(profile.investment_horizon)
                if profile.investment_horizon in INVESTMENT_HORIZONS else 1,
                help=INVESTMENT_HORIZONS.get(profile.investment_horizon, "")
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

        leverage_allowed = st.checkbox(
            "레버리지 사용 허용",
            value=profile.leverage_allowed,
            help="선물/마진 거래 허용 여부"
        )

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
                min_value=10,
                max_value=480,
                value=profile.available_time_per_day,
                step=10,
                help="하루에 차트를 볼 수 있는 시간"
            )

        st.divider()
        st.subheader("활성 거래 시간")

        col3, col4 = st.columns(2)

        with col3:
            active_start = st.time_input(
                "시작 시간",
                value=None,
                help="거래를 시작하는 시간"
            )
            if active_start:
                active_hours_start = active_start.strftime("%H:%M")
            else:
                active_hours_start = profile.active_hours_start

        with col4:
            active_end = st.time_input(
                "종료 시간",
                value=None,
                help="거래를 종료하는 시간"
            )
            if active_end:
                active_hours_end = active_end.strftime("%H:%M")
            else:
                active_hours_end = profile.active_hours_end

        st.caption(f"현재 설정: {active_hours_start} ~ {active_hours_end}")

        st.divider()
        st.subheader("관심 코인 설정")

        # 기본 코인 목록
        available_coins = ["BTC", "ETH", "XRP", "SOL", "DOGE", "ADA", "AVAX", "MATIC", "LINK", "DOT"]

        preferred_coins = st.multiselect(
            "관심 코인 선택",
            options=available_coins,
            default=[c for c in profile.preferred_coins if c in available_coins],
            help="AI가 주로 분석할 코인들"
        )

        # 커스텀 코인 추가
        custom_coin = st.text_input(
            "다른 코인 추가 (심볼)",
            placeholder="예: SHIB",
            help="목록에 없는 코인을 추가합니다"
        )

        if custom_coin and custom_coin.upper() not in preferred_coins:
            if st.button(f"'{custom_coin.upper()}' 추가"):
                preferred_coins.append(custom_coin.upper())
                st.rerun()

    with tab3:
        st.subheader("투자 경험 및 기술 수준")

        col1, col2 = st.columns(2)

        with col1:
            experience_years = st.number_input(
                "투자 경력 (년)",
                min_value=0.0,
                max_value=30.0,
                value=profile.experience_years,
                step=0.5,
                help="암호화폐 투자 경력"
            )

        with col2:
            technical_skill = st.selectbox(
                "기술적 분석 수준",
                options=list(SKILL_LEVELS.keys()),
                index=list(SKILL_LEVELS.keys()).index(profile.technical_analysis_skill)
                if profile.technical_analysis_skill in SKILL_LEVELS else 0,
                format_func=lambda x: f"{x} - {SKILL_LEVELS[x].split(' - ')[1]}"
            )

        st.info(
            "💡 기술 수준에 따라 AI의 설명 난이도가 조절됩니다. "
            "초보자에게는 쉬운 설명을, 고급 사용자에게는 상세한 분석을 제공합니다."
        )

    with tab4:
        st.subheader("과거 투자 실수 (자기 인식)")
        st.caption("솔직하게 체크하면 AI가 해당 실수를 반복하지 않도록 경고해줍니다")

        past_mistakes = []

        col1, col2 = st.columns(2)

        for i, mistake in enumerate(COMMON_MISTAKES):
            col = col1 if i < len(COMMON_MISTAKES) // 2 else col2
            with col:
                if st.checkbox(
                    mistake,
                    value=mistake in profile.past_major_mistakes,
                    key=f"mistake_{i}"
                ):
                    past_mistakes.append(mistake)

        # 커스텀 실수 추가
        custom_mistake = st.text_input(
            "기타 실수 (직접 입력)",
            placeholder="예: 밤늦게 음주 매매",
        )

        if custom_mistake:
            past_mistakes.append(custom_mistake)

        if past_mistakes:
            st.warning(f"인식한 약점: {', '.join(past_mistakes)}")

    # 저장 버튼
    st.divider()

    col_save, col_reset = st.columns([3, 1])

    with col_save:
        if st.button("💾 프로필 저장", type="primary", use_container_width=True):
            # 프로필 객체 생성
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

            # DB에 저장
            try:
                db.save_profile(new_profile)
                st.success("프로필이 저장되었습니다!")
                st.balloons()
            except Exception as e:
                st.error(f"저장 중 오류가 발생했습니다: {e}")

    with col_reset:
        if st.button("🔄 초기화", use_container_width=True):
            # 기본값으로 초기화
            default_profile = InvestorProfile()
            try:
                db.save_profile(default_profile)
                st.success("프로필이 초기화되었습니다")
                st.rerun()
            except Exception as e:
                st.error(f"초기화 중 오류가 발생했습니다: {e}")

    # 현재 프로필 요약
    st.divider()
    st.subheader("📋 현재 프로필 요약")

    if existing_profile:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("총 자본금", f"{existing_profile.total_capital:,}원")
            st.metric("1회 리스크", f"{existing_profile.risk_per_trade * 100:.1f}%")

        with col2:
            st.metric("투자 목표", existing_profile.investment_goal)
            st.metric("거래 스타일", existing_profile.trading_style)

        with col3:
            st.metric("리스크 성향", existing_profile.risk_tolerance)
            st.metric("투자 경력", f"{existing_profile.experience_years}년")


if __name__ == "__main__":
    st.set_page_config(page_title="프로필 설정", layout="wide")
    render_profile_page()
