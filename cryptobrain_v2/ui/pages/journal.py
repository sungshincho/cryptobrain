"""
CryptoBrain V2 - 매매일지 페이지
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd

from ...database.models import TradeHistory
from ...database.db_manager import DBManager
from ...config.settings import (
    DB_PATH,
    DEFAULT_COINS,
    MARKET_CONDITIONS,
    TRIGGER_REASONS,
    EMOTIONAL_STATES,
    TRADE_TAGS,
    format_krw,
    format_percent,
)


def render_journal_page():
    """매매일지 페이지 렌더링"""
    st.header("📝 매매일지")
    st.caption("거래 기록을 관리하고 패턴을 분석하세요")

    # DB 연결
    db = DBManager(str(DB_PATH))

    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 거래 통계",
        "📋 거래 기록",
        "➕ 새 거래 추가",
        "🔍 패턴 분석"
    ])

    with tab1:
        render_trade_stats(db)

    with tab2:
        render_trade_history(db)

    with tab3:
        render_add_trade_form(db)

    with tab4:
        render_pattern_analysis(db)


def render_trade_stats(db: DBManager):
    """거래 통계 표시"""
    st.subheader("거래 성과 통계")

    stats = db.get_trade_stats()

    if stats["total_trades"] == 0:
        st.info("아직 기록된 거래가 없습니다. '새 거래 추가' 탭에서 거래를 기록하세요.")
        return

    # 핵심 지표
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "총 거래 수",
            f"{stats['total_trades']}회",
            help="전체 거래 횟수"
        )

    with col2:
        win_rate = stats.get('win_rate', 0)
        st.metric(
            "승률",
            f"{win_rate:.1f}%",
            delta="좋음" if win_rate >= 50 else "개선필요",
            delta_color="normal" if win_rate >= 50 else "inverse"
        )

    with col3:
        pf = stats.get('profit_factor', 0)
        st.metric(
            "손익비",
            f"{pf:.2f}",
            delta="좋음" if pf >= 1.5 else "개선필요",
            delta_color="normal" if pf >= 1.5 else "inverse",
            help="총 수익 / 총 손실"
        )

    with col4:
        total_pnl = stats.get('total_profit', 0) - stats.get('total_loss', 0)
        st.metric(
            "순손익",
            format_krw(total_pnl),
            delta="수익" if total_pnl > 0 else "손실",
            delta_color="normal" if total_pnl >= 0 else "inverse"
        )

    st.divider()

    # 상세 통계
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**수익 거래**")
        st.write(f"- 승리 횟수: {stats.get('wins', 0)}회")
        st.write(f"- 평균 수익: {format_krw(stats.get('avg_win', 0))}")
        st.write(f"- 최대 수익: {format_krw(stats.get('best_trade', 0))}")

    with col2:
        st.markdown("**손실 거래**")
        st.write(f"- 패배 횟수: {stats.get('losses', 0)}회")
        st.write(f"- 평균 손실: {format_krw(stats.get('avg_loss', 0))}")
        st.write(f"- 최대 손실: {format_krw(stats.get('worst_trade', 0))}")

    # 평균 보유 기간
    avg_holding = stats.get('avg_holding_period', 0)
    if avg_holding > 0:
        if avg_holding < 24:
            holding_text = f"{avg_holding:.1f}시간"
        else:
            holding_text = f"{avg_holding/24:.1f}일"
        st.info(f"평균 보유 기간: {holding_text}")


def render_trade_history(db: DBManager):
    """거래 기록 표시"""
    st.subheader("거래 기록")

    # 필터
    col1, col2, col3 = st.columns(3)

    with col1:
        symbol_filter = st.selectbox(
            "종목 필터",
            options=["전체"] + [c.split("/")[0] for c in DEFAULT_COINS],
            index=0
        )

    with col2:
        side_filter = st.selectbox(
            "거래 유형",
            options=["전체", "매수", "매도"],
            index=0
        )

    with col3:
        limit = st.selectbox(
            "표시 개수",
            options=[10, 25, 50, 100],
            index=1
        )

    # 필터 적용
    symbol = f"{symbol_filter}/KRW" if symbol_filter != "전체" else None
    side = {"매수": "buy", "매도": "sell"}.get(side_filter)

    trades = db.get_trades(symbol=symbol, side=side, limit=limit)

    if not trades:
        st.info("조건에 맞는 거래 기록이 없습니다")
        return

    # 거래 목록 표시
    for trade in trades:
        with st.expander(
            f"{'🟢' if trade.side == 'buy' else '🔴'} "
            f"{trade.symbol} | "
            f"{'매수' if trade.side == 'buy' else '매도'} | "
            f"{trade.timestamp.strftime('%Y-%m-%d %H:%M') if trade.timestamp else '날짜 없음'}"
        ):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write(f"**수량:** {trade.quantity:.8f}")
                st.write(f"**가격:** {format_krw(trade.price)}")
                st.write(f"**금액:** {format_krw(trade.quantity * trade.price)}")

            with col2:
                st.write(f"**시장 상황:** {MARKET_CONDITIONS.get(trade.market_condition, trade.market_condition)}")
                st.write(f"**매매 이유:** {trade.trigger_reason}")
                st.write(f"**감정 상태:** {trade.emotional_state}")

            with col3:
                if trade.pnl is not None:
                    pnl_color = "green" if trade.pnl >= 0 else "red"
                    st.markdown(f"**손익:** :{pnl_color}[{format_krw(trade.pnl)}]")
                    st.markdown(f"**손익률:** :{pnl_color}[{trade.pnl_pct:+.2f}%]")

                if trade.holding_period:
                    if trade.holding_period < 24:
                        st.write(f"**보유 기간:** {trade.holding_period}시간")
                    else:
                        st.write(f"**보유 기간:** {trade.holding_period/24:.1f}일")

            if trade.tags:
                st.write(f"**태그:** {', '.join(trade.tags)}")

            if trade.notes:
                st.write(f"**메모:** {trade.notes}")

            if trade.ai_recommendation:
                with st.container():
                    st.markdown("**당시 AI 추천:**")
                    st.caption(trade.ai_recommendation[:200] + "..." if len(trade.ai_recommendation) > 200 else trade.ai_recommendation)


def render_add_trade_form(db: DBManager):
    """새 거래 추가 폼"""
    st.subheader("새 거래 기록 추가")

    # 매수/매도 선택
    side = st.radio(
        "거래 유형",
        ["매수 (Buy)", "매도 (Sell)"],
        horizontal=True
    )
    trade_side = "buy" if "매수" in side else "sell"

    with st.form("add_trade_form"):
        col1, col2 = st.columns(2)

        with col1:
            # 종목 선택
            coin_options = [c.split("/")[0] for c in DEFAULT_COINS]
            selected_coin = st.selectbox(
                "코인",
                options=coin_options + ["기타"]
            )

            if selected_coin == "기타":
                custom_coin = st.text_input("코인 심볼", placeholder="예: SHIB")
                symbol = f"{custom_coin.upper()}/KRW" if custom_coin else ""
            else:
                symbol = f"{selected_coin}/KRW"

            quantity = st.number_input(
                "수량",
                min_value=0.0,
                value=0.0,
                format="%.8f"
            )

            price = st.number_input(
                "거래 가격 (KRW)",
                min_value=0,
                value=0,
                step=1000
            )

            trade_date = st.date_input(
                "거래 날짜",
                value=datetime.now().date()
            )

            trade_time = st.time_input(
                "거래 시간",
                value=datetime.now().time()
            )

        with col2:
            st.markdown("**매매 맥락 (AI 학습용)**")

            market_condition = st.selectbox(
                "당시 시장 상황",
                options=list(MARKET_CONDITIONS.keys()),
                format_func=lambda x: MARKET_CONDITIONS[x]
            )

            trigger_reason = st.selectbox(
                "매매 이유",
                options=list(TRIGGER_REASONS.keys()),
                format_func=lambda x: f"{x}"
            )

            emotional_state = st.selectbox(
                "감정 상태",
                options=list(EMOTIONAL_STATES.keys()),
                format_func=lambda x: f"{x} - {EMOTIONAL_STATES[x]}"
            )

            tags = st.multiselect(
                "태그",
                options=TRADE_TAGS,
                help="해당되는 태그를 모두 선택하세요"
            )

            notes = st.text_area(
                "메모",
                placeholder="거래에 대한 메모를 남겨주세요"
            )

        # 매도인 경우 손익 입력
        pnl = None
        pnl_pct = None
        holding_period = None
        related_trade_id = None

        if trade_side == "sell":
            st.divider()
            st.markdown("**손익 정보 (매도 시)**")

            col1, col2, col3 = st.columns(3)

            with col1:
                pnl = st.number_input(
                    "손익 금액 (KRW)",
                    value=0,
                    step=10000,
                    help="양수: 수익, 음수: 손실"
                )

            with col2:
                pnl_pct = st.number_input(
                    "손익률 (%)",
                    value=0.0,
                    step=0.5
                )

            with col3:
                holding_period = st.number_input(
                    "보유 기간 (시간)",
                    min_value=0,
                    value=0,
                    help="매수 후 얼마나 보유했나요?"
                )

        submitted = st.form_submit_button("거래 기록 추가", type="primary")

        if submitted:
            if not symbol or quantity <= 0 or price <= 0:
                st.error("종목, 수량, 가격을 올바르게 입력해주세요")
            else:
                timestamp = datetime.combine(trade_date, trade_time)

                trade = TradeHistory(
                    symbol=symbol,
                    side=trade_side,
                    quantity=quantity,
                    price=price,
                    timestamp=timestamp,
                    market_condition=market_condition,
                    trigger_reason=trigger_reason,
                    emotional_state=emotional_state,
                    pnl=pnl if trade_side == "sell" else None,
                    pnl_pct=pnl_pct if trade_side == "sell" else None,
                    holding_period=holding_period if trade_side == "sell" else None,
                    related_trade_id=related_trade_id,
                    tags=tags,
                    notes=notes,
                )

                try:
                    trade_id = db.add_trade(trade)
                    st.success(f"거래가 기록되었습니다! (ID: {trade_id})")
                    st.balloons()
                except Exception as e:
                    st.error(f"저장 실패: {e}")


def render_pattern_analysis(db: DBManager):
    """패턴 분석"""
    st.subheader("투자 패턴 분석")

    stats = db.get_trade_stats()

    if stats["total_closed_trades"] < 5:
        st.info("패턴 분석을 위해 최소 5건 이상의 완료된 거래가 필요합니다.")
        return

    # 매매 이유별 분석
    st.markdown("### 매매 이유별 성과")
    trigger_stats = db.get_trades_by_trigger()

    if trigger_stats:
        trigger_data = []
        for reason, data in trigger_stats.items():
            trigger_data.append({
                "매매 이유": reason,
                "거래 수": data["count"],
                "승률 (%)": f"{data['win_rate']:.1f}",
                "평균 수익률 (%)": f"{data['avg_pnl_pct']:.2f}"
            })

        if trigger_data:
            st.dataframe(trigger_data, use_container_width=True, hide_index=True)

            # 최고/최저 성과 이유
            best_trigger = max(trigger_stats.items(), key=lambda x: x[1]["win_rate"])
            worst_trigger = min(trigger_stats.items(), key=lambda x: x[1]["win_rate"])

            col1, col2 = st.columns(2)
            with col1:
                st.success(f"✅ 최고 성과: '{best_trigger[0]}' (승률 {best_trigger[1]['win_rate']:.1f}%)")
            with col2:
                st.error(f"❌ 최저 성과: '{worst_trigger[0]}' (승률 {worst_trigger[1]['win_rate']:.1f}%)")

    st.divider()

    # 감정 상태별 분석
    st.markdown("### 감정 상태별 성과")
    emotion_stats = db.get_trades_by_emotion()

    if emotion_stats:
        emotion_data = []
        for emotion, data in emotion_stats.items():
            emotion_data.append({
                "감정 상태": emotion,
                "거래 수": data["count"],
                "승률 (%)": f"{data['win_rate']:.1f}",
                "평균 수익률 (%)": f"{data['avg_pnl_pct']:.2f}"
            })

        if emotion_data:
            st.dataframe(emotion_data, use_container_width=True, hide_index=True)

            # 차트
            fig = px.bar(
                emotion_data,
                x="감정 상태",
                y="승률 (%)",
                color="승률 (%)",
                color_continuous_scale=["red", "yellow", "green"]
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # 개선 제안
    st.markdown("### 💡 개선 제안")

    suggestions = []

    # 승률 기반 제안
    win_rate = stats.get("win_rate", 0)
    if win_rate < 50:
        suggestions.append("승률이 50% 미만입니다. 진입 시점을 더 신중하게 선택하세요.")

    # 손익비 기반 제안
    profit_factor = stats.get("profit_factor", 0)
    if profit_factor < 1.5:
        suggestions.append("손익비가 낮습니다. 손절을 빠르게, 익절을 더 멀리 설정해보세요.")

    # 감정 기반 제안
    if emotion_stats:
        anxious_stats = emotion_stats.get("불안", {})
        if anxious_stats.get("win_rate", 100) < 40:
            suggestions.append("불안한 상태에서의 거래 성과가 좋지 않습니다. 불안할 때는 거래를 피하세요.")

        fomo_excited = emotion_stats.get("흥분", {})
        if fomo_excited.get("win_rate", 100) < 40:
            suggestions.append("흥분 상태에서의 거래 성과가 좋지 않습니다. 냉정을 유지하세요.")

    # 트리거 기반 제안
    if trigger_stats:
        fomo_stats = trigger_stats.get("FOMO", {})
        if fomo_stats.get("win_rate", 100) < 40:
            suggestions.append("FOMO 매수의 성과가 좋지 않습니다. 급하게 매수하지 마세요.")

    if suggestions:
        for suggestion in suggestions:
            st.warning(f"💡 {suggestion}")
    else:
        st.success("현재 거래 패턴이 양호합니다. 계속 유지하세요!")


if __name__ == "__main__":
    st.set_page_config(page_title="매매일지", layout="wide")
    render_journal_page()
