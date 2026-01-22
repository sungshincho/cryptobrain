"""
CryptoBrain V2 - 기술적 분석 모듈
각종 기술적 지표 계산 및 시그널 생성
"""
import pandas as pd
import numpy as np
from typing import Optional

from ..config.settings import (
    MA_PERIODS,
    EMA_PERIODS,
    RSI_PERIOD,
    RSI_OVERSOLD,
    RSI_OVERBOUGHT,
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
    BB_PERIOD,
    BB_STD,
    ATR_PERIOD,
)


class TechnicalAnalyzer:
    """기술적 분석기"""

    def __init__(self, df: pd.DataFrame):
        """
        Args:
            df: OHLCV DataFrame (columns: timestamp, open, high, low, close, volume)
        """
        self.df = df.copy()
        self._validate_dataframe()

    def _validate_dataframe(self):
        """DataFrame 유효성 검사"""
        required_columns = ["open", "high", "low", "close", "volume"]
        missing = [col for col in required_columns if col not in self.df.columns]
        if missing:
            raise ValueError(f"필수 컬럼 누락: {missing}")

    # ==================== 이동평균 ====================

    def sma(self, period: int) -> pd.Series:
        """단순이동평균 (SMA)"""
        return self.df["close"].rolling(window=period).mean()

    def ema(self, period: int) -> pd.Series:
        """지수이동평균 (EMA)"""
        return self.df["close"].ewm(span=period, adjust=False).mean()

    def add_ma_indicators(self) -> "TechnicalAnalyzer":
        """모든 이동평균 지표 추가"""
        for period in MA_PERIODS:
            self.df[f"SMA_{period}"] = self.sma(period)

        for period in EMA_PERIODS:
            self.df[f"EMA_{period}"] = self.ema(period)

        return self

    # ==================== 모멘텀 지표 ====================

    def rsi(self, period: int = RSI_PERIOD) -> pd.Series:
        """RSI (Relative Strength Index)"""
        delta = self.df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def macd(self) -> tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD (Moving Average Convergence Divergence)

        Returns:
            (MACD Line, Signal Line, Histogram)
        """
        ema_fast = self.df["close"].ewm(span=MACD_FAST, adjust=False).mean()
        ema_slow = self.df["close"].ewm(span=MACD_SLOW, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def stochastic(
        self,
        k_period: int = 14,
        d_period: int = 3
    ) -> tuple[pd.Series, pd.Series]:
        """
        스토캐스틱 오실레이터

        Returns:
            (%K, %D)
        """
        lowest_low = self.df["low"].rolling(window=k_period).min()
        highest_high = self.df["high"].rolling(window=k_period).max()

        stoch_k = 100 * (self.df["close"] - lowest_low) / (highest_high - lowest_low)
        stoch_d = stoch_k.rolling(window=d_period).mean()

        return stoch_k, stoch_d

    # ==================== 변동성 지표 ====================

    def bollinger_bands(
        self,
        period: int = BB_PERIOD,
        std: float = BB_STD
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """
        볼린저 밴드

        Returns:
            (Upper, Middle, Lower)
        """
        middle = self.df["close"].rolling(window=period).mean()
        std_dev = self.df["close"].rolling(window=period).std()

        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)

        return upper, middle, lower

    def atr(self, period: int = ATR_PERIOD) -> pd.Series:
        """ATR (Average True Range)"""
        high = self.df["high"]
        low = self.df["low"]
        close = self.df["close"].shift(1)

        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()

        return atr

    def atr_percent(self, period: int = ATR_PERIOD) -> pd.Series:
        """ATR 퍼센트 (변동성 비율)"""
        return (self.atr(period) / self.df["close"]) * 100

    # ==================== 거래량 지표 ====================

    def volume_sma(self, period: int = 20) -> pd.Series:
        """거래량 이동평균"""
        return self.df["volume"].rolling(window=period).mean()

    def volume_ratio(self, period: int = 20) -> pd.Series:
        """거래량 비율 (현재/평균)"""
        avg_volume = self.volume_sma(period)
        return self.df["volume"] / avg_volume

    def obv(self) -> pd.Series:
        """OBV (On-Balance Volume)"""
        obv = [0]
        for i in range(1, len(self.df)):
            if self.df["close"].iloc[i] > self.df["close"].iloc[i-1]:
                obv.append(obv[-1] + self.df["volume"].iloc[i])
            elif self.df["close"].iloc[i] < self.df["close"].iloc[i-1]:
                obv.append(obv[-1] - self.df["volume"].iloc[i])
            else:
                obv.append(obv[-1])
        return pd.Series(obv, index=self.df.index)

    # ==================== 지지/저항 ====================

    def support_resistance_levels(
        self,
        lookback: int = 20,
        threshold: float = 0.02
    ) -> dict[str, list[float]]:
        """
        지지/저항선 계산

        Args:
            lookback: 분석할 캔들 수
            threshold: 유의미한 레벨 판단 임계값

        Returns:
            {"support": [...], "resistance": [...]}
        """
        recent = self.df.tail(lookback)
        current_price = self.df["close"].iloc[-1]

        # 최근 고점/저점 찾기
        highs = recent["high"].values
        lows = recent["low"].values

        support_levels = []
        resistance_levels = []

        # 로컬 최저점 찾기 (지지선)
        for i in range(1, len(lows) - 1):
            if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                if lows[i] < current_price:
                    support_levels.append(lows[i])

        # 로컬 최고점 찾기 (저항선)
        for i in range(1, len(highs) - 1):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                if highs[i] > current_price:
                    resistance_levels.append(highs[i])

        # 중복 제거 및 정렬
        support_levels = sorted(set(support_levels), reverse=True)[:3]
        resistance_levels = sorted(set(resistance_levels))[:3]

        return {
            "support": support_levels,
            "resistance": resistance_levels,
        }

    # ==================== 전체 지표 계산 ====================

    def calculate_all(self) -> pd.DataFrame:
        """모든 지표 계산"""
        # 이동평균
        self.add_ma_indicators()

        # RSI
        self.df["RSI"] = self.rsi()

        # MACD
        macd_line, signal_line, histogram = self.macd()
        self.df["MACD"] = macd_line
        self.df["MACD_Signal"] = signal_line
        self.df["MACD_Hist"] = histogram

        # 볼린저 밴드
        upper, middle, lower = self.bollinger_bands()
        self.df["BB_Upper"] = upper
        self.df["BB_Middle"] = middle
        self.df["BB_Lower"] = lower

        # ATR
        self.df["ATR"] = self.atr()
        self.df["ATR_Pct"] = self.atr_percent()

        # 거래량
        self.df["Volume_SMA"] = self.volume_sma()
        self.df["Volume_Ratio"] = self.volume_ratio()

        # 스토캐스틱
        stoch_k, stoch_d = self.stochastic()
        self.df["Stoch_K"] = stoch_k
        self.df["Stoch_D"] = stoch_d

        return self.df

    # ==================== 시그널 생성 ====================

    def get_signals(self) -> dict:
        """
        종합 시그널 반환

        Returns:
            {
                "trend": "bullish" | "bearish" | "neutral",
                "strength": 0-100,
                "rsi_signal": "oversold" | "overbought" | "neutral",
                "macd_signal": "golden_cross" | "death_cross" | "neutral",
                "bb_signal": "lower_touch" | "upper_touch" | "neutral",
                "volume_signal": "high" | "low" | "normal",
                "support_levels": [...],
                "resistance_levels": [...],
                "recommendation": "buy" | "sell" | "hold",
            }
        """
        # 지표 계산 확인
        if "RSI" not in self.df.columns:
            self.calculate_all()

        latest = self.df.iloc[-1]
        prev = self.df.iloc[-2] if len(self.df) > 1 else latest

        signals = {}

        # 추세 판단
        if "SMA_20" in self.df.columns and "SMA_50" in self.df.columns:
            sma20 = latest["SMA_20"]
            sma50 = latest["SMA_50"]
            if pd.notna(sma20) and pd.notna(sma50):
                if latest["close"] > sma20 > sma50:
                    signals["trend"] = "bullish"
                elif latest["close"] < sma20 < sma50:
                    signals["trend"] = "bearish"
                else:
                    signals["trend"] = "neutral"
            else:
                signals["trend"] = "neutral"
        else:
            signals["trend"] = "neutral"

        # RSI 시그널
        rsi_value = latest["RSI"]
        if pd.notna(rsi_value):
            if rsi_value < RSI_OVERSOLD:
                signals["rsi_signal"] = "oversold"
            elif rsi_value > RSI_OVERBOUGHT:
                signals["rsi_signal"] = "overbought"
            else:
                signals["rsi_signal"] = "neutral"
            signals["rsi_value"] = round(rsi_value, 2)
        else:
            signals["rsi_signal"] = "neutral"
            signals["rsi_value"] = 50

        # MACD 시그널
        if pd.notna(latest["MACD"]) and pd.notna(latest["MACD_Signal"]):
            if prev["MACD"] < prev["MACD_Signal"] and latest["MACD"] > latest["MACD_Signal"]:
                signals["macd_signal"] = "golden_cross"
            elif prev["MACD"] > prev["MACD_Signal"] and latest["MACD"] < latest["MACD_Signal"]:
                signals["macd_signal"] = "death_cross"
            else:
                signals["macd_signal"] = "neutral"
        else:
            signals["macd_signal"] = "neutral"

        # 볼린저 밴드 시그널
        if pd.notna(latest["BB_Lower"]) and pd.notna(latest["BB_Upper"]):
            if latest["close"] <= latest["BB_Lower"]:
                signals["bb_signal"] = "lower_touch"
            elif latest["close"] >= latest["BB_Upper"]:
                signals["bb_signal"] = "upper_touch"
            else:
                signals["bb_signal"] = "neutral"
        else:
            signals["bb_signal"] = "neutral"

        # 거래량 시그널
        if pd.notna(latest["Volume_Ratio"]):
            if latest["Volume_Ratio"] > 2.0:
                signals["volume_signal"] = "high"
            elif latest["Volume_Ratio"] < 0.5:
                signals["volume_signal"] = "low"
            else:
                signals["volume_signal"] = "normal"
        else:
            signals["volume_signal"] = "normal"

        # 지지/저항선
        sr_levels = self.support_resistance_levels()
        signals["support_levels"] = sr_levels["support"]
        signals["resistance_levels"] = sr_levels["resistance"]

        # 종합 점수 및 추천
        score = self._calculate_signal_score(signals)
        signals["strength"] = score

        if score >= 70:
            signals["recommendation"] = "buy"
        elif score <= 30:
            signals["recommendation"] = "sell"
        else:
            signals["recommendation"] = "hold"

        # ATR 정보 추가
        signals["atr"] = latest["ATR"] if pd.notna(latest["ATR"]) else 0
        signals["atr_pct"] = latest["ATR_Pct"] if pd.notna(latest["ATR_Pct"]) else 0
        signals["current_price"] = latest["close"]

        return signals

    def _calculate_signal_score(self, signals: dict) -> int:
        """시그널 점수 계산 (0-100)"""
        score = 50  # 기본 중립

        # 추세
        if signals["trend"] == "bullish":
            score += 15
        elif signals["trend"] == "bearish":
            score -= 15

        # RSI
        if signals["rsi_signal"] == "oversold":
            score += 20
        elif signals["rsi_signal"] == "overbought":
            score -= 20

        # MACD
        if signals["macd_signal"] == "golden_cross":
            score += 15
        elif signals["macd_signal"] == "death_cross":
            score -= 15

        # 볼린저 밴드
        if signals["bb_signal"] == "lower_touch":
            score += 10
        elif signals["bb_signal"] == "upper_touch":
            score -= 10

        # 범위 제한
        return max(0, min(100, score))

    def get_analysis_text(self) -> str:
        """분석 결과를 텍스트로 반환"""
        signals = self.get_signals()

        trend_text = {
            "bullish": "상승 추세",
            "bearish": "하락 추세",
            "neutral": "중립/횡보",
        }

        rsi_text = {
            "oversold": f"과매도 구간 (RSI: {signals['rsi_value']})",
            "overbought": f"과매수 구간 (RSI: {signals['rsi_value']})",
            "neutral": f"중립 구간 (RSI: {signals['rsi_value']})",
        }

        macd_text = {
            "golden_cross": "골든크로스 발생 (매수 시그널)",
            "death_cross": "데드크로스 발생 (매도 시그널)",
            "neutral": "MACD 중립",
        }

        text = f"""
📊 기술적 분석 결과

• 추세: {trend_text.get(signals['trend'], '알 수 없음')}
• RSI: {rsi_text.get(signals['rsi_signal'], '알 수 없음')}
• MACD: {macd_text.get(signals['macd_signal'], '알 수 없음')}
• 볼린저밴드: {signals['bb_signal']}
• 거래량: {signals['volume_signal']}
• ATR 변동성: {signals['atr_pct']:.2f}%

📍 지지선: {', '.join([f'{p:,.0f}' for p in signals['support_levels']]) or '없음'}
📍 저항선: {', '.join([f'{p:,.0f}' for p in signals['resistance_levels']]) or '없음'}

📈 종합 점수: {signals['strength']}/100
💡 추천: {signals['recommendation'].upper()}
"""
        return text.strip()


if __name__ == "__main__":
    # 테스트
    import ccxt

    exchange = ccxt.upbit()
    ohlcv = exchange.fetch_ohlcv("BTC/KRW", "1h", limit=100)
    df = pd.DataFrame(
        ohlcv,
        columns=["timestamp", "open", "high", "low", "close", "volume"]
    )

    analyzer = TechnicalAnalyzer(df)
    analyzer.calculate_all()

    print("=== 분석 결과 ===")
    print(analyzer.get_analysis_text())

    print("\n=== 시그널 상세 ===")
    signals = analyzer.get_signals()
    for key, value in signals.items():
        print(f"{key}: {value}")
