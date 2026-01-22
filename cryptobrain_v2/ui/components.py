"""
CryptoBrain V2 - 재사용 가능한 UI 컴포넌트
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional

from ..config.settings import format_krw, format_percent


def render_metric_card(
    title: str,
    value: str,
    delta: Optional[str] = None,
    delta_color: str = "normal",
    help_text: Optional[str] = None
):
    """메트릭 카드 컴포넌트"""
    st.metric(
        label=title,
        value=value,
        delta=delta,
        delta_color=delta_color,
        help=help_text
    )


def render_coin_card(
    symbol: str,
    price: float,
    change: float,
    rsi: float,
    trend: str
):
    """코인 정보 카드"""
    coin = symbol.split("/")[0]
    trend_emoji = "📈" if trend == "bullish" else "📉"
    change_color = "green" if change >= 0 else "red"

    st.markdown(f"""
    **{coin}** {trend_emoji}
    - 가격: {format_krw(price)}
    - RSI: {rsi:.1f}
    - :{change_color}[{change:+.2f}%]
    """)


def render_candlestick_chart(
    df: pd.DataFrame,
    title: str = "",
    height: int = 400
) -> go.Figure:
    """캔들스틱 차트 생성"""
    fig = go.Figure(data=[
        go.Candlestick(
            x=df["timestamp"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="OHLC"
        )
    ])

    # 이동평균선 추가
    if "SMA_20" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df["SMA_20"],
            mode="lines",
            name="SMA 20",
            line=dict(color="orange", width=1)
        ))

    if "SMA_50" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df["SMA_50"],
            mode="lines",
            name="SMA 50",
            line=dict(color="blue", width=1)
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title="Price (KRW)",
        height=height,
        xaxis_rangeslider_visible=False,
        template="plotly_dark"
    )

    return fig


def render_rsi_chart(
    df: pd.DataFrame,
    height: int = 200
) -> go.Figure:
    """RSI 차트 생성"""
    if "RSI" not in df.columns:
        return None

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["RSI"],
        mode="lines",
        name="RSI",
        line=dict(color="purple", width=1.5)
    ))

    # 과매수/과매도 라인
    fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="과매수")
    fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="과매도")
    fig.add_hline(y=50, line_dash="dot", line_color="gray")

    fig.update_layout(
        title="RSI",
        height=height,
        yaxis_range=[0, 100],
        template="plotly_dark"
    )

    return fig


def render_volume_chart(
    df: pd.DataFrame,
    height: int = 150
) -> go.Figure:
    """거래량 차트 생성"""
    colors = ["green" if c >= o else "red"
              for o, c in zip(df["open"], df["close"])]

    fig = go.Figure(data=[
        go.Bar(
            x=df["timestamp"],
            y=df["volume"],
            marker_color=colors,
            name="Volume"
        )
    ])

    fig.update_layout(
        title="Volume",
        height=height,
        template="plotly_dark"
    )

    return fig


def render_portfolio_pie_chart(
    allocation: dict,
    height: int = 300
) -> go.Figure:
    """포트폴리오 파이 차트"""
    labels = list(allocation.keys())
    values = list(allocation.values())

    fig = px.pie(
        values=values,
        names=labels,
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set2
    )

    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        showlegend=False,
        margin=dict(t=0, b=0, l=0, r=0),
        height=height
    )

    return fig


def render_pnl_bar_chart(
    trades: list,
    height: int = 300
) -> go.Figure:
    """손익 바 차트"""
    if not trades:
        return None

    dates = []
    pnls = []
    colors = []

    for trade in trades:
        if trade.pnl is not None:
            dates.append(trade.timestamp.strftime("%m/%d") if trade.timestamp else "")
            pnls.append(trade.pnl)
            colors.append("green" if trade.pnl >= 0 else "red")

    fig = go.Figure(data=[
        go.Bar(
            x=dates,
            y=pnls,
            marker_color=colors
        )
    ])

    fig.update_layout(
        title="거래별 손익",
        height=height,
        template="plotly_dark"
    )

    return fig


def render_signal_indicator(
    signal: str,
    value: float,
    thresholds: tuple = (30, 70)
) -> None:
    """시그널 인디케이터"""
    low, high = thresholds

    if value < low:
        color = "green"
        status = "과매도"
    elif value > high:
        color = "red"
        status = "과매수"
    else:
        color = "gray"
        status = "중립"

    st.markdown(f"""
    **{signal}**: :{color}[{value:.1f}] ({status})
    """)


def render_trade_summary_card(
    stats: dict
) -> None:
    """거래 요약 카드"""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "승률",
            f"{stats.get('win_rate', 0):.1f}%",
            delta="좋음" if stats.get('win_rate', 0) >= 50 else "개선필요"
        )

    with col2:
        st.metric(
            "손익비",
            f"{stats.get('profit_factor', 0):.2f}",
            delta="좋음" if stats.get('profit_factor', 0) >= 1.5 else "개선필요"
        )

    with col3:
        total_pnl = stats.get('total_profit', 0) - stats.get('total_loss', 0)
        st.metric(
            "순손익",
            format_krw(total_pnl),
            delta="수익" if total_pnl > 0 else "손실"
        )


def render_warning_box(
    message: str,
    warning_type: str = "warning"
) -> None:
    """경고 박스"""
    if warning_type == "error":
        st.error(f"🚫 {message}")
    elif warning_type == "warning":
        st.warning(f"⚠️ {message}")
    elif warning_type == "info":
        st.info(f"ℹ️ {message}")
    else:
        st.success(f"✅ {message}")


def render_loading_spinner(text: str = "로딩 중..."):
    """로딩 스피너 컨텍스트 매니저"""
    return st.spinner(text)


if __name__ == "__main__":
    # 테스트
    st.set_page_config(page_title="컴포넌트 테스트", layout="wide")
    st.title("UI 컴포넌트 테스트")

    col1, col2, col3 = st.columns(3)

    with col1:
        render_metric_card("총 자산", "5,000,000원", "+10%")

    with col2:
        render_metric_card("승률", "65%", "좋음")

    with col3:
        render_metric_card("손익비", "1.8", "좋음")

    st.divider()

    render_coin_card("BTC/KRW", 50000000, 2.5, 45, "bullish")

    render_warning_box("테스트 경고 메시지입니다", "warning")
