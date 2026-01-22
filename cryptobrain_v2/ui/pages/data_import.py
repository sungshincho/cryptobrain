"""
CryptoBrain V2 - 데이터 임포트 페이지
거래소 CSV 파일 업로드 및 거래 데이터 관리
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from cryptobrain_v2.config.settings import DB_PATH, format_krw, format_percent
from cryptobrain_v2.database.db_manager import DBManager
from cryptobrain_v2.core.data_import import (
    DataImporter,
    get_supported_exchanges,
)


def render_data_import_page():
    """데이터 임포트 페이지 렌더링"""
    st.header("📥 데이터 임포트")

    db = DBManager(str(DB_PATH))

    # 탭 구성
    tab_import, tab_history, tab_analysis = st.tabs([
        "📤 파일 업로드",
        "📋 임포트 이력",
        "📊 거래 분석"
    ])

    with tab_import:
        render_import_tab(db)

    with tab_history:
        render_history_tab(db)

    with tab_analysis:
        render_analysis_tab(db)


def render_import_tab(db: DBManager):
    """파일 업로드 탭"""
    st.subheader("거래소 CSV 파일 업로드")

    # 지원 거래소 정보
    exchanges = get_supported_exchanges()

    col1, col2 = st.columns([2, 1])

    with col1:
        exchange_options = {e["display_name"]: e["name"] for e in exchanges}
        selected_display = st.selectbox(
            "거래소 선택",
            options=list(exchange_options.keys()),
            index=0
        )
        selected_exchange = exchange_options[selected_display]

    with col2:
        # 해당 거래소 다운로드 안내
        for e in exchanges:
            if e["name"] == selected_exchange:
                st.info(f"💡 {e['notes']}")
                break

    # 파일 업로드
    uploaded_file = st.file_uploader(
        "CSV 파일 선택",
        type=["csv"],
        help="거래소에서 다운로드한 CSV 파일을 업로드하세요"
    )

    if uploaded_file:
        st.divider()
        render_import_preview(db, uploaded_file, selected_exchange)


def render_import_preview(db: DBManager, uploaded_file, exchange: str):
    """임포트 미리보기 및 실행"""

    # 파일 파싱
    try:
        importer = DataImporter(exchange)
        file_content = uploaded_file.getvalue()
        result = importer.parse_csv(file_content)

        if not result.success:
            st.error("파일 파싱 실패")
            for error in result.errors:
                st.error(error)
            return

        # 미리보기 통계
        st.subheader("📊 파싱 결과")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("전체 행", f"{result.total_rows:,}건")

        with col2:
            st.metric("파싱 성공", f"{result.parsed_rows:,}건")

        with col3:
            st.metric("스킵", f"{result.skipped_rows:,}건")

        with col4:
            st.metric("종목 수", f"{len(result.symbols_traded)}개")

        # 날짜 범위
        if result.date_range[0] and result.date_range[1]:
            start_str = result.date_range[0].strftime("%Y-%m-%d")
            end_str = result.date_range[1].strftime("%Y-%m-%d")
            st.info(f"📅 기간: {start_str} ~ {end_str}")

        # 금액 요약
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("총 매수금액", format_krw(result.total_buy_amount))

        with col2:
            st.metric("총 매도금액", format_krw(result.total_sell_amount))

        with col3:
            st.metric("총 수수료", format_krw(result.total_fee))

        # 종목별 요약
        st.subheader("📈 종목별 요약")

        symbol_data = {}
        for trade in result.trades:
            sym = trade.symbol
            if sym not in symbol_data:
                symbol_data[sym] = {
                    "매수": 0,
                    "매도": 0,
                    "매수금액": 0,
                    "매도금액": 0,
                }

            if trade.trade_type.value == "buy":
                symbol_data[sym]["매수"] += 1
                symbol_data[sym]["매수금액"] += trade.total_amount
            else:
                symbol_data[sym]["매도"] += 1
                symbol_data[sym]["매도금액"] += trade.total_amount

        symbol_df = pd.DataFrame([
            {
                "종목": sym,
                "매수 횟수": data["매수"],
                "매도 횟수": data["매도"],
                "매수금액": format_krw(data["매수금액"]),
                "매도금액": format_krw(data["매도금액"]),
            }
            for sym, data in symbol_data.items()
        ])
        st.dataframe(symbol_df, use_container_width=True, hide_index=True)

        # 경고 메시지
        if result.warnings:
            with st.expander(f"⚠️ 경고 ({len(result.warnings)}건)"):
                for warning in result.warnings[:20]:  # 최대 20개만 표시
                    st.warning(warning)

        st.divider()

        # FIFO 손익 계산 옵션
        calculate_pnl = st.checkbox(
            "FIFO 방식 손익 계산",
            value=True,
            help="매도 거래의 실현 손익을 FIFO(선입선출) 방식으로 자동 계산합니다"
        )

        # 임포트 실행
        if st.button("✅ 데이터 저장", type="primary", use_container_width=True):
            with st.spinner("데이터 저장 중..."):
                # FIFO 계산
                trades = result.trades
                if calculate_pnl and trades:
                    trades, symbol_stats = importer.calculate_fifo_pnl(trades)

                # DB 저장
                save_result = db.save_imported_trades(
                    trades=trades,
                    exchange=exchange,
                    file_name=uploaded_file.name,
                )

                st.success(f"✅ {save_result['saved_count']:,}건 저장 완료! (배치 ID: {save_result['batch_id']})")

                # FIFO 손익 요약
                if calculate_pnl:
                    total_pnl = sum(t.realized_pnl or 0 for t in trades if t.realized_pnl)
                    if total_pnl != 0:
                        st.metric(
                            "총 실현손익 (FIFO)",
                            format_krw(total_pnl),
                            delta="수익" if total_pnl > 0 else "손실"
                        )

    except Exception as e:
        st.error(f"오류 발생: {str(e)}")
        import traceback
        with st.expander("상세 오류"):
            st.code(traceback.format_exc())


def render_history_tab(db: DBManager):
    """임포트 이력 탭"""
    st.subheader("📋 임포트 이력")

    batches = db.get_import_batches(limit=20)

    if not batches:
        st.info("임포트 이력이 없습니다")
        return

    for batch in batches:
        with st.expander(
            f"📦 {batch['exchange'].upper()} - {batch['file_name'] or '파일명 없음'} "
            f"({batch['parsed_rows']}건)"
        ):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**배치 ID:** {batch['batch_id']}")
                st.write(f"**거래소:** {batch['exchange']}")
                st.write(f"**파싱 건수:** {batch['parsed_rows']:,}건")
                st.write(f"**임포트 일시:** {batch['created_at']}")

            with col2:
                st.write(f"**총 매수:** {format_krw(batch['total_buy_amount'])}")
                st.write(f"**총 매도:** {format_krw(batch['total_sell_amount'])}")
                st.write(f"**총 수수료:** {format_krw(batch['total_fee'])}")

                if batch['date_range_start'] and batch['date_range_end']:
                    st.write(f"**기간:** {batch['date_range_start'][:10]} ~ {batch['date_range_end'][:10]}")

            # 삭제 버튼
            if st.button(f"🗑️ 삭제", key=f"delete_{batch['batch_id']}"):
                if db.delete_import_batch(batch['batch_id']):
                    st.success("삭제되었습니다")
                    st.rerun()
                else:
                    st.error("삭제 실패")


def render_analysis_tab(db: DBManager):
    """거래 분석 탭"""
    st.subheader("📊 거래 분석")

    # 전체 통계
    stats = db.get_imported_trade_stats()

    if stats["total_trades"] == 0:
        st.info("분석할 거래 데이터가 없습니다. CSV 파일을 먼저 업로드해주세요.")
        return

    # 요약 메트릭
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("총 거래 건수", f"{stats['total_trades']:,}건")

    with col2:
        st.metric("거래 종목 수", f"{stats['unique_symbols']:,}개")

    with col3:
        st.metric("총 실현손익", format_krw(stats["total_realized_pnl"]))

    with col4:
        st.metric(
            "승률",
            f"{stats['win_rate']:.1f}%",
            delta="좋음" if stats['win_rate'] >= 50 else "개선 필요"
        )

    st.divider()

    # 금액 통계
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("총 매수금액", format_krw(stats["total_buy_amount"]))

    with col2:
        st.metric("총 매도금액", format_krw(stats["total_sell_amount"]))

    with col3:
        st.metric("총 수수료", format_krw(stats["total_fee"]))

    # 승/패 통계
    if stats["win_count"] + stats["loss_count"] > 0:
        st.divider()
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("수익 거래", f"{stats['win_count']:,}건")

        with col2:
            st.metric("손실 거래", f"{stats['loss_count']:,}건")

        with col3:
            avg_win = stats['avg_win'] or 0
            avg_loss = abs(stats['avg_loss'] or 0)
            profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
            st.metric(
                "손익비",
                f"{profit_factor:.2f}",
                delta="좋음" if profit_factor >= 1.5 else "개선 필요"
            )

    st.divider()

    # 종목별 요약
    st.subheader("📈 종목별 요약")

    symbol_summary = db.get_symbol_summary_from_imports()

    if symbol_summary:
        df = pd.DataFrame([
            {
                "종목": item["symbol"],
                "거래 횟수": item["trade_count"],
                "현재 보유량": f"{item['current_quantity']:.8f}".rstrip('0').rstrip('.'),
                "평균 매수가": format_krw(item["avg_buy_price"]),
                "총 매수": format_krw(item["total_buy_amount"]),
                "총 매도": format_krw(item["total_sell_amount"]),
                "실현손익": format_krw(item["total_pnl"] or 0),
            }
            for item in symbol_summary
        ])

        st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    # 최근 거래 내역
    st.subheader("📝 최근 거래 내역")

    # 필터
    col1, col2 = st.columns(2)

    with col1:
        filter_symbol = st.selectbox(
            "종목 필터",
            options=["전체"] + [item["symbol"] for item in symbol_summary],
            index=0
        )

    with col2:
        filter_type = st.selectbox(
            "거래 유형",
            options=["전체", "매수", "매도"],
            index=0
        )

    # 거래 내역 조회
    trades = db.get_imported_trades(
        symbol=filter_symbol if filter_symbol != "전체" else None,
        trade_type="buy" if filter_type == "매수" else ("sell" if filter_type == "매도" else None),
        limit=50
    )

    if trades:
        trade_df = pd.DataFrame([
            {
                "일시": t["timestamp"][:16] if t["timestamp"] else "",
                "유형": "매수" if t["trade_type"] == "buy" else "매도",
                "종목": t["symbol"],
                "수량": f"{t['quantity']:.8f}".rstrip('0').rstrip('.'),
                "단가": format_krw(t["price"]),
                "금액": format_krw(t["total_amount"]),
                "수수료": format_krw(t["fee"]),
                "실현손익": format_krw(t["realized_pnl"]) if t["realized_pnl"] else "-",
            }
            for t in trades
        ])

        st.dataframe(trade_df, use_container_width=True, hide_index=True)
    else:
        st.info("조건에 맞는 거래가 없습니다")


if __name__ == "__main__":
    st.set_page_config(page_title="데이터 임포트", layout="wide")
    render_data_import_page()
