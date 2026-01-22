"""
CryptoBrain V2 - 포트폴리오 관리 페이지
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from ...database.models import Position
from ...database.db_manager import DBManager
from ...config.settings import DB_PATH, DEFAULT_COINS, format_krw, format_percent


def render_portfolio_page():
    """포트폴리오 관리 페이지 렌더링"""
    st.header("💼 포트폴리오 관리")
    st.caption("보유 종목과 현금을 관리하세요")

    # DB 연결
    db = DBManager(str(DB_PATH))

    # 탭 구성
    tab1, tab2, tab3 = st.tabs([
        "📊 포트폴리오 현황",
        "➕ 포지션 추가/수정",
        "💵 현금 관리"
    ])

    with tab1:
        render_portfolio_overview(db)

    with tab2:
        render_position_form(db)

    with tab3:
        render_cash_management(db)


def render_portfolio_overview(db: DBManager):
    """포트폴리오 현황 표시"""
    st.subheader("포트폴리오 현황")

    # 포트폴리오 요약 조회
    summary = db.get_portfolio_summary()
    cash = db.get_cash_balance()

    # 요약 메트릭
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "총 자산",
            format_krw(summary.total_value + cash),
            help="보유 코인 평가금 + 현금"
        )

    with col2:
        st.metric(
            "투자금",
            format_krw(summary.total_invested),
            help="코인 매수에 사용한 총 금액"
        )

    with col3:
        pnl_delta = f"{summary.total_pnl_pct:+.2f}%" if summary.total_invested > 0 else None
        st.metric(
            "평가손익",
            format_krw(summary.total_pnl),
            delta=pnl_delta
        )

    with col4:
        st.metric(
            "현금",
            format_krw(cash),
            help="사용 가능한 현금"
        )

    st.divider()

    # 보유 포지션이 있는 경우
    if summary.positions:
        col_chart, col_list = st.columns([1, 1])

        with col_chart:
            st.subheader("자산 비중")

            # 파이 차트 데이터 준비
            chart_data = []
            for pos in summary.positions:
                if pos.current_value > 0:
                    coin = pos.symbol.split("/")[0]
                    chart_data.append({
                        "asset": coin,
                        "value": pos.current_value
                    })

            if cash > 0:
                chart_data.append({
                    "asset": "현금",
                    "value": cash
                })

            if chart_data:
                fig = px.pie(
                    chart_data,
                    values="value",
                    names="asset",
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(
                    showlegend=False,
                    margin=dict(t=0, b=0, l=0, r=0),
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)

        with col_list:
            st.subheader("보유 종목")

            for pos in summary.positions:
                with st.container():
                    coin = pos.symbol.split("/")[0]
                    pnl_color = "green" if pos.unrealized_pnl >= 0 else "red"

                    st.markdown(f"""
                    **{coin}** ({pos.symbol})
                    - 수량: {pos.quantity:.8f}
                    - 평균단가: {format_krw(pos.avg_entry_price)}
                    - 현재가: {format_krw(pos.current_price)}
                    - 평가금: {format_krw(pos.current_value)}
                    - 손익: :{pnl_color}[{format_krw(pos.unrealized_pnl)} ({pos.unrealized_pnl_pct:+.2f}%)]
                    """)
                    st.divider()

        # 집중 리스크 경고
        if summary.concentration_risk == "high":
            st.warning(
                f"⚠️ 집중 리스크 경고: {summary.largest_position}의 비중이 높습니다. "
                "분산 투자를 고려해보세요."
            )

    else:
        st.info("아직 등록된 포지션이 없습니다. '포지션 추가' 탭에서 보유 종목을 등록하세요.")

    # 포지션 상세 테이블
    if summary.positions:
        st.subheader("포지션 상세")

        table_data = []
        for pos in summary.positions:
            table_data.append({
                "종목": pos.symbol,
                "수량": f"{pos.quantity:.8f}",
                "평균단가": f"{pos.avg_entry_price:,.0f}",
                "현재가": f"{pos.current_price:,.0f}",
                "평가금": f"{pos.current_value:,.0f}",
                "손익": f"{pos.unrealized_pnl:,.0f}",
                "손익률": f"{pos.unrealized_pnl_pct:+.2f}%",
            })

        st.dataframe(table_data, use_container_width=True, hide_index=True)


def render_position_form(db: DBManager):
    """포지션 추가/수정 폼"""
    st.subheader("포지션 추가/수정")

    # 모드 선택
    mode = st.radio(
        "작업 선택",
        ["새 포지션 추가", "기존 포지션 수정", "포지션 삭제"],
        horizontal=True
    )

    if mode == "새 포지션 추가":
        render_add_position_form(db)
    elif mode == "기존 포지션 수정":
        render_edit_position_form(db)
    else:
        render_delete_position_form(db)


def render_add_position_form(db: DBManager):
    """새 포지션 추가 폼"""
    with st.form("add_position_form"):
        st.markdown("**새 포지션 등록**")

        col1, col2 = st.columns(2)

        with col1:
            # 코인 선택
            coin_options = [c.split("/")[0] for c in DEFAULT_COINS]
            selected_coin = st.selectbox(
                "코인 선택",
                options=coin_options + ["기타"],
                index=0
            )

            if selected_coin == "기타":
                custom_coin = st.text_input("코인 심볼 입력", placeholder="예: SHIB")
                symbol = f"{custom_coin.upper()}/KRW" if custom_coin else ""
            else:
                symbol = f"{selected_coin}/KRW"

            quantity = st.number_input(
                "수량",
                min_value=0.0,
                value=0.0,
                format="%.8f",
                help="보유하고 있는 수량"
            )

        with col2:
            avg_price = st.number_input(
                "평균 매수가 (KRW)",
                min_value=0,
                value=0,
                step=1000,
                help="평균 매수 단가"
            )

            current_price = st.number_input(
                "현재가 (KRW)",
                min_value=0,
                value=0,
                step=1000,
                help="현재 시장 가격 (자동 업데이트됨)"
            )

            buy_date = st.date_input(
                "최초 매수일",
                value=datetime.now().date()
            )

        submitted = st.form_submit_button("포지션 추가", type="primary")

        if submitted:
            if not symbol or quantity <= 0 or avg_price <= 0:
                st.error("모든 필드를 올바르게 입력해주세요")
            else:
                position = Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_entry_price=avg_price,
                    current_price=current_price if current_price > 0 else avg_price,
                    first_buy_date=datetime.combine(buy_date, datetime.min.time()),
                    last_buy_date=datetime.now()
                )

                try:
                    db.save_position(position)
                    st.success(f"{symbol} 포지션이 추가되었습니다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: {e}")


def render_edit_position_form(db: DBManager):
    """기존 포지션 수정 폼"""
    positions = db.get_positions()

    if not positions:
        st.info("수정할 포지션이 없습니다")
        return

    # 포지션 선택
    position_options = {p.symbol: p for p in positions}
    selected_symbol = st.selectbox(
        "수정할 포지션 선택",
        options=list(position_options.keys())
    )

    if selected_symbol:
        pos = position_options[selected_symbol]

        with st.form("edit_position_form"):
            st.markdown(f"**{selected_symbol} 수정**")

            col1, col2 = st.columns(2)

            with col1:
                new_quantity = st.number_input(
                    "수량",
                    min_value=0.0,
                    value=pos.quantity,
                    format="%.8f"
                )

                new_avg_price = st.number_input(
                    "평균 매수가 (KRW)",
                    min_value=0,
                    value=int(pos.avg_entry_price),
                    step=1000
                )

            with col2:
                new_current_price = st.number_input(
                    "현재가 (KRW)",
                    min_value=0,
                    value=int(pos.current_price),
                    step=1000
                )

            submitted = st.form_submit_button("수정 저장", type="primary")

            if submitted:
                updated_pos = Position(
                    symbol=pos.symbol,
                    quantity=new_quantity,
                    avg_entry_price=new_avg_price,
                    current_price=new_current_price,
                    first_buy_date=pos.first_buy_date,
                    last_buy_date=datetime.now()
                )

                try:
                    db.save_position(updated_pos)
                    st.success("포지션이 수정되었습니다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"수정 실패: {e}")


def render_delete_position_form(db: DBManager):
    """포지션 삭제 폼"""
    positions = db.get_positions()

    if not positions:
        st.info("삭제할 포지션이 없습니다")
        return

    position_options = [p.symbol for p in positions]
    selected_symbol = st.selectbox(
        "삭제할 포지션 선택",
        options=position_options
    )

    st.warning(f"⚠️ '{selected_symbol}' 포지션을 삭제하시겠습니까?")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("삭제", type="primary", use_container_width=True):
            try:
                db.delete_position(selected_symbol)
                st.success("포지션이 삭제되었습니다!")
                st.rerun()
            except Exception as e:
                st.error(f"삭제 실패: {e}")

    with col2:
        if st.button("취소", use_container_width=True):
            st.rerun()


def render_cash_management(db: DBManager):
    """현금 관리"""
    st.subheader("현금 잔고 관리")

    current_cash = db.get_cash_balance()

    st.metric("현재 현금 잔고", format_krw(current_cash))

    with st.form("cash_form"):
        new_cash = st.number_input(
            "새 현금 잔고 (KRW)",
            min_value=0,
            value=int(current_cash),
            step=100000,
            help="보유하고 있는 현금 (KRW)"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.form_submit_button("저장", type="primary", use_container_width=True):
                try:
                    db.set_cash_balance(new_cash)
                    st.success("현금 잔고가 업데이트되었습니다!")
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: {e}")

    st.divider()

    # 빠른 입출금
    st.subheader("빠른 입출금")

    col1, col2 = st.columns(2)

    with col1:
        deposit = st.number_input(
            "입금액",
            min_value=0,
            value=0,
            step=100000,
            key="deposit"
        )
        if st.button("입금", use_container_width=True):
            if deposit > 0:
                db.set_cash_balance(current_cash + deposit)
                st.success(f"{format_krw(deposit)} 입금 완료!")
                st.rerun()

    with col2:
        withdraw = st.number_input(
            "출금액",
            min_value=0,
            max_value=int(current_cash),
            value=0,
            step=100000,
            key="withdraw"
        )
        if st.button("출금", use_container_width=True):
            if withdraw > 0:
                db.set_cash_balance(current_cash - withdraw)
                st.success(f"{format_krw(withdraw)} 출금 완료!")
                st.rerun()


if __name__ == "__main__":
    st.set_page_config(page_title="포트폴리오", layout="wide")
    render_portfolio_page()
