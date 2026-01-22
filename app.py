import streamlit as st
import ccxt
import pandas as pd
import google.generativeai as genai
import os

# ---------------------------------------------------------
# 1. 설정 및 API 키 처리 (자동 로그인 기능)
# ---------------------------------------------------------
st.set_page_config(page_title="CryptoBrain AI", page_icon="🧠", layout="wide")

# Streamlit Cloud의 Secrets에서 키를 가져오거나, 없으면 사이드바에서 입력받음
api_key = st.secrets.get("GOOGLE_API_KEY", None)

if not api_key:
    with st.sidebar:
        st.header("🔑 로그인")
        api_key = st.text_input("Google AI API Key", type="password")
        if not api_key:
            st.warning("API 키를 입력하거나 Secrets에 설정해주세요.")
            st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-pro-002')

# 사용자 자본금 설정 (기본값 100만원)
CAPITAL = 1000000 

# ---------------------------------------------------------
# 2. 데이터 수집 함수 (오류 방지 및 캐싱)
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def get_market_data():
    exchange = ccxt.upbit()
    symbols = ["BTC/KRW", "ETH/KRW", "XRP/KRW", "SOL/KRW", "DOGE/KRW"]
    data = {}
    
    for sym in symbols:
        try:
            ohlcv = exchange.fetch_ohlcv(sym, timeframe='1h', limit=30)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # 기술적 지표 계산
            df['MA20'] = df['close'].rolling(20).mean()
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            latest = df.iloc[-1]
            data[sym] = {
                "price": latest['close'],
                "rsi": latest['RSI'],
                "trend": "상승 📈" if latest['close'] > latest['MA20'] else "하락 📉",
                "volume": latest['volume']
            }
        except Exception as e:
            continue
    return data

# ---------------------------------------------------------
# 3. AI 분석 엔진
# ---------------------------------------------------------
def ask_ai(query, context):
    system_instruction = f"""
    당신은 20년 경력의 가상화폐 전업 투자자 'CryptoBrain'입니다.
    현재 자본금: {CAPITAL:,.0f} KRW.
    
    [실시간 시장 데이터]
    {context}
    
    [미션]
    1. 사용자의 질문에 대해 위 데이터와 당신의 지식(Google Search 활용 가능 시)을 결합해 답변하세요.
    2. 매수 추천 시: 진입가, 목표가, 손절가를 명확히 제시하세요.
    3. 말투: 전문적이고 냉철하게. (예: "현재 진입은 위험합니다.")
    """
    
    try:
        response = model.generate_content([system_instruction, query])
        return response.text
    except Exception as e:
        return f"죄송합니다. AI 분석 중 오류가 발생했습니다: {e}"

# ---------------------------------------------------------
# 4. 메인 UI
# ---------------------------------------------------------
st.title("🧠 CryptoBrain V1")
st.caption("실시간 업비트 시세 기반 AI 투자 어시스턴트")

if st.button("🔄 데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()

# 데이터 로딩
with st.spinner('시장 데이터를 스캔 중입니다...'):
    market_data = get_market_data()
    
# 요약 정보를 텍스트로 변환 (AI에게 줄 데이터)
context_str = ""
for sym, info in market_data.items():
    context_str += f"- {sym}: {info['price']:,.0f}원 (RSI: {info['rsi']:.1f}, 추세: {info['trend']})\n"

# 탭 구성
tab1, tab2 = st.tabs(["📊 오늘의 전략", "💬 AI 대화"])

with tab1:
    st.header("오늘의 매매 추천")
    st.write("AI가 전체 시장을 스캔하여 추천 종목을 선별합니다.")
    if st.button("🚀 AI 분석 리포트 생성"):
        with st.spinner("차트 패턴과 뉴스를 분석 중..."):
            prompt = "현재 시장 데이터를 종합적으로 분석해서, 오늘 당장 매수할만한 종목이 있는지 알려줘. 없다면 관망하라고 해. 표로 정리해줘."
            result = ask_ai(prompt, context_str)
            st.markdown(result)
            
    st.divider()
    st.subheader("실시간 시세판")
    cols = st.columns(3)
    for i, (sym, info) in enumerate(market_data.items()):
        with cols[i % 3]:
            st.metric(label=sym, value=f"{info['price']:,.0f}", delta=info['trend'])
            st.caption(f"RSI: {info['rsi']:.1f}")

with tab2:
    st.header("투자 상담소")
    
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "어떤 종목이 궁금하신가요? (예: 리플 지금 사도 돼?)"}]

    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input():
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("생각 중..."):
                response = ask_ai(prompt, context_str)
                st.write(response)

                st.session_state.messages.append({"role": "assistant", "content": response})

