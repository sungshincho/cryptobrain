"""
CryptoBrain V3 - 시장 분석 엔진

시장 상황을 종합 분석하여 최적의 거래 방향 제시
추세, 지표, 지지/저항, 변동성을 종합 판단
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, Optional
import pandas as pd
import numpy as np


class MarketRegime(Enum):
    """시장 국면"""
    STRONG_BULL = "강세 상승"
    BULL = "상승"
    NEUTRAL = "횡보"
    BEAR = "하락"
    STRONG_BEAR = "강세 하락"
    HIGH_VOLATILITY = "고변동성"


class TrendStrength(Enum):
    """추세 강도"""
    STRONG = "강함"
    MODERATE = "보통"
    WEAK = "약함"
    NO_TREND = "추세 없음"


@dataclass
class MarketContext:
    """시장 맥락 분석 결과"""

    # 추세
    regime: MarketRegime
    trend_direction: str           # "up" | "down" | "sideways"
    trend_strength: TrendStrength
    trend_strength_value: str      # for EV calculator

    # 기술적 지표
    rsi: float
    rsi_signal: str                # "oversold" | "neutral" | "overbought"
    macd_signal: str               # "bullish" | "neutral" | "bearish"
    ma_alignment: str              # "bullish" | "neutral" | "bearish"

    # 지지/저항
    nearest_support: float
    nearest_resistance: float
    distance_to_support_pct: float
    distance_to_resistance_pct: float

    # 변동성
    atr_percent: float             # ATR을 %로 환산
    volatility_regime: str         # "low" | "normal" | "high" | "extreme"

    # 거래량
    volume_trend: str              # "increasing" | "decreasing" | "stable"
    volume_anomaly: bool           # 이상 거래량 여부

    # 종합 점수
    bullish_score: float           # 0~100 (매수 유리도)
    bearish_score: float           # 0~100 (매도 유리도)

    # 최적 전략 제안
    recommended_strategy: str      # "long" | "short" | "wait" | "scalp"
    reasoning: list = field(default_factory=list)

    # 현재가
    current_price: float = 0

    def to_dict(self) -> dict:
        return {
            "regime": self.regime.value,
            "trend_direction": self.trend_direction,
            "trend_strength": self.trend_strength.value,
            "trend_strength_value": self.trend_strength_value,
            "rsi": self.rsi,
            "rsi_signal": self.rsi_signal,
            "macd_signal": self.macd_signal,
            "ma_alignment": self.ma_alignment,
            "nearest_support": self.nearest_support,
            "nearest_resistance": self.nearest_resistance,
            "distance_to_support_pct": self.distance_to_support_pct,
            "distance_to_resistance_pct": self.distance_to_resistance_pct,
            "atr_percent": self.atr_percent,
            "volatility_regime": self.volatility_regime,
            "volume_trend": self.volume_trend,
            "volume_anomaly": self.volume_anomaly,
            "bullish_score": self.bullish_score,
            "bearish_score": self.bearish_score,
            "recommended_strategy": self.recommended_strategy,
            "reasoning": self.reasoning,
            "current_price": self.current_price,
        }


class MarketAnalyzer:
    """
    시장 상황을 종합 분석하여 최적의 거래 방향 제시
    """

    def __init__(self):
        pass

    def analyze(self, df: pd.DataFrame, symbol: str = "") -> MarketContext:
        """
        OHLCV 데이터를 분석하여 시장 맥락 생성

        Args:
            df: OHLCV 데이터 (columns: open, high, low, close, volume, timestamp)
            symbol: 심볼명

        Returns:
            MarketContext: 시장 맥락 분석 결과
        """
        # 데이터가 부족하면 기본값 반환
        if len(df) < 50:
            return self._get_default_context()

        # 기술적 지표 계산
        df = self._calculate_indicators(df)

        latest = df.iloc[-1]
        current_price = latest['close']

        # 추세 분석
        regime = self._determine_regime(df)
        trend_dir, trend_str = self._analyze_trend(df)

        # RSI 분석
        rsi = latest['RSI'] if pd.notna(latest.get('RSI')) else 50
        rsi_signal = "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral"

        # MACD 분석
        macd_signal = self._analyze_macd(df)

        # MA 정렬 분석
        ma_alignment = self._analyze_ma_alignment(df)

        # 지지/저항 찾기
        support, resistance = self._find_sr_levels(df)

        # 거리 계산
        dist_support = ((current_price - support) / current_price) * 100 if support > 0 else 100
        dist_resistance = ((resistance - current_price) / current_price) * 100 if resistance > 0 else 100

        # 변동성 분석
        atr = latest.get('ATR', 0)
        atr_pct = (atr / current_price) * 100 if current_price > 0 and pd.notna(atr) else 2
        vol_regime = self._classify_volatility(atr_pct)

        # 거래량 분석
        vol_trend, vol_anomaly = self._analyze_volume(df)

        # 종합 점수 계산
        bull_score, bear_score = self._calculate_bias_scores(
            rsi, macd_signal, ma_alignment, trend_dir, vol_trend
        )

        # 전략 추천
        strategy, reasoning = self._recommend_strategy(
            regime, trend_dir, trend_str, bull_score, bear_score,
            current_price, support, resistance, vol_regime
        )

        return MarketContext(
            regime=regime,
            trend_direction=trend_dir,
            trend_strength=trend_str,
            trend_strength_value=trend_str.value.lower() if isinstance(trend_str, TrendStrength) else "moderate",
            rsi=round(rsi, 1),
            rsi_signal=rsi_signal,
            macd_signal=macd_signal,
            ma_alignment=ma_alignment,
            nearest_support=round(support, 0),
            nearest_resistance=round(resistance, 0),
            distance_to_support_pct=round(dist_support, 2),
            distance_to_resistance_pct=round(dist_resistance, 2),
            atr_percent=round(atr_pct, 2),
            volatility_regime=vol_regime,
            volume_trend=vol_trend,
            volume_anomaly=vol_anomaly,
            bullish_score=round(bull_score, 1),
            bearish_score=round(bear_score, 1),
            recommended_strategy=strategy,
            reasoning=reasoning,
            current_price=round(current_price, 0),
        )

    def _get_default_context(self) -> MarketContext:
        """기본 컨텍스트 반환 (데이터 부족 시)"""
        return MarketContext(
            regime=MarketRegime.NEUTRAL,
            trend_direction="sideways",
            trend_strength=TrendStrength.NO_TREND,
            trend_strength_value="weak",
            rsi=50,
            rsi_signal="neutral",
            macd_signal="neutral",
            ma_alignment="neutral",
            nearest_support=0,
            nearest_resistance=0,
            distance_to_support_pct=0,
            distance_to_resistance_pct=0,
            atr_percent=2,
            volatility_regime="normal",
            volume_trend="stable",
            volume_anomaly=False,
            bullish_score=50,
            bearish_score=50,
            recommended_strategy="wait",
            reasoning=["데이터 부족 - 분석 불가"],
            current_price=0,
        )

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        df = df.copy()

        # 컬럼명 소문자 통일
        df.columns = [c.lower() for c in df.columns]

        # 이동평균
        df['SMA20'] = df['close'].rolling(20).mean()
        df['SMA50'] = df['close'].rolling(50).mean()
        df['SMA200'] = df['close'].rolling(min(200, len(df))).mean()
        df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()

        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        df['RSI'] = 100 - (100 / (1 + rs))
        df['RSI'] = df['RSI'].fillna(50)

        # MACD
        df['MACD'] = df['EMA12'] - df['EMA26']
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()

        # 볼린저 밴드
        df['BB_Mid'] = df['close'].rolling(20).mean()
        df['BB_Std'] = df['close'].rolling(20).std()
        df['BB_Upper'] = df['BB_Mid'] + 2 * df['BB_Std']
        df['BB_Lower'] = df['BB_Mid'] - 2 * df['BB_Std']

        # 거래량 이동평균
        df['Vol_SMA'] = df['volume'].rolling(20).mean()

        return df

    def _determine_regime(self, df: pd.DataFrame) -> MarketRegime:
        """시장 국면 판단"""
        latest = df.iloc[-1]
        price = latest['close']

        # 200일 이평선 대비 위치
        sma200 = latest.get('SMA200')
        if pd.notna(sma200) and sma200 > 0:
            above_200 = price > sma200
            distance_200 = (price - sma200) / sma200 * 100
        else:
            sma50 = latest.get('SMA50', price)
            above_200 = price > sma50
            distance_200 = 0

        # RSI
        rsi = latest.get('RSI', 50)

        # 변동성
        atr = latest.get('ATR', 0)
        atr_pct = (atr / price) * 100 if price > 0 and pd.notna(atr) else 2

        # 고변동성 체크
        if atr_pct > 5:
            return MarketRegime.HIGH_VOLATILITY

        # 국면 판단
        if above_200 and distance_200 > 15 and rsi > 55:
            return MarketRegime.STRONG_BULL
        elif above_200 and distance_200 > 0:
            return MarketRegime.BULL
        elif not above_200 and distance_200 < -15 and rsi < 45:
            return MarketRegime.STRONG_BEAR
        elif not above_200:
            return MarketRegime.BEAR
        else:
            return MarketRegime.NEUTRAL

    def _analyze_trend(self, df: pd.DataFrame) -> Tuple[str, TrendStrength]:
        """추세 방향 및 강도 분석"""
        latest = df.iloc[-1]
        price = latest['close']

        sma20 = latest.get('SMA20', price)
        sma50 = latest.get('SMA50', price)

        # 추세 방향
        if pd.notna(sma20) and pd.notna(sma50):
            if price > sma20 > sma50:
                direction = "up"
            elif price < sma20 < sma50:
                direction = "down"
            else:
                direction = "sideways"
        else:
            direction = "sideways"

        # 추세 강도 (최근 20봉의 방향성)
        if len(df) >= 20:
            recent = df.tail(20)
            up_candles = len(recent[recent['close'] > recent['open']])
            down_candles = 20 - up_candles

            ratio = max(up_candles, down_candles) / 20

            if ratio > 0.7:
                strength = TrendStrength.STRONG
            elif ratio > 0.55:
                strength = TrendStrength.MODERATE
            elif ratio > 0.45:
                strength = TrendStrength.WEAK
            else:
                strength = TrendStrength.NO_TREND
        else:
            strength = TrendStrength.WEAK

        return direction, strength

    def _analyze_macd(self, df: pd.DataFrame) -> str:
        """MACD 분석"""
        if len(df) < 2:
            return "neutral"

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        macd = latest.get('MACD', 0)
        signal = latest.get('MACD_Signal', 0)
        hist = latest.get('MACD_Hist', 0)
        prev_hist = prev.get('MACD_Hist', 0)

        if pd.isna(macd) or pd.isna(signal):
            return "neutral"

        # 골든/데드 크로스 확인
        if macd > signal and prev.get('MACD', 0) <= prev.get('MACD_Signal', 0):
            return "bullish"  # 골든 크로스
        elif macd < signal and prev.get('MACD', 0) >= prev.get('MACD_Signal', 0):
            return "bearish"  # 데드 크로스

        # 히스토그램 방향
        if hist > 0 and hist > prev_hist:
            return "bullish"
        elif hist < 0 and hist < prev_hist:
            return "bearish"

        return "neutral"

    def _analyze_ma_alignment(self, df: pd.DataFrame) -> str:
        """이동평균선 정렬 분석"""
        latest = df.iloc[-1]
        price = latest['close']

        sma20 = latest.get('SMA20', price)
        sma50 = latest.get('SMA50', price)
        sma200 = latest.get('SMA200', price)

        if pd.isna(sma20) or pd.isna(sma50):
            return "neutral"

        # 완전 정배열 (강세)
        if price > sma20 > sma50:
            if pd.notna(sma200) and sma50 > sma200:
                return "bullish"
            return "bullish"

        # 완전 역배열 (약세)
        if price < sma20 < sma50:
            if pd.notna(sma200) and sma50 < sma200:
                return "bearish"
            return "bearish"

        return "neutral"

    def _find_sr_levels(self, df: pd.DataFrame) -> Tuple[float, float]:
        """지지/저항 레벨 찾기 (피봇 포인트 방식)"""
        if len(df) < 20:
            latest = df.iloc[-1]
            return latest['low'], latest['high']

        recent = df.tail(50)
        current_price = df.iloc[-1]['close']

        # 최근 저점들 (지지선 후보)
        lows = recent['low'].values
        highs = recent['high'].values

        # 현재가 아래의 가장 가까운 지지선
        supports = lows[lows < current_price]
        if len(supports) > 0:
            # 가장 빈번하게 터치된 레벨 근처
            nearest_support = supports.max()
        else:
            nearest_support = lows.min()

        # 현재가 위의 가장 가까운 저항선
        resistances = highs[highs > current_price]
        if len(resistances) > 0:
            nearest_resistance = resistances.min()
        else:
            nearest_resistance = highs.max()

        return nearest_support, nearest_resistance

    def _classify_volatility(self, atr_percent: float) -> str:
        """변동성 분류"""
        if atr_percent < 1.5:
            return "low"
        elif atr_percent < 3:
            return "normal"
        elif atr_percent < 5:
            return "high"
        else:
            return "extreme"

    def _analyze_volume(self, df: pd.DataFrame) -> Tuple[str, bool]:
        """거래량 분석"""
        if len(df) < 20:
            return "stable", False

        latest = df.iloc[-1]
        vol_sma = latest.get('Vol_SMA', 0)
        current_vol = latest.get('volume', 0)

        if pd.isna(vol_sma) or vol_sma == 0:
            return "stable", False

        # 거래량 추세
        recent_vols = df.tail(5)['volume'].values
        if len(recent_vols) >= 5:
            trend = np.polyfit(range(5), recent_vols, 1)[0]
            if trend > vol_sma * 0.1:
                vol_trend = "increasing"
            elif trend < -vol_sma * 0.1:
                vol_trend = "decreasing"
            else:
                vol_trend = "stable"
        else:
            vol_trend = "stable"

        # 이상 거래량 감지 (평균의 2배 이상)
        vol_anomaly = current_vol > vol_sma * 2

        return vol_trend, vol_anomaly

    def _calculate_bias_scores(
        self,
        rsi: float,
        macd_signal: str,
        ma_alignment: str,
        trend_direction: str,
        volume_trend: str
    ) -> Tuple[float, float]:
        """매수/매도 유리 점수 계산 (0~100)"""

        bull_score = 50
        bear_score = 50

        # RSI 기여 (최대 ±20점)
        if rsi < 30:
            bull_score += 20
            bear_score -= 10
        elif rsi < 40:
            bull_score += 10
            bear_score -= 5
        elif rsi > 70:
            bear_score += 20
            bull_score -= 10
        elif rsi > 60:
            bear_score += 10
            bull_score -= 5

        # MACD 기여 (최대 ±15점)
        if macd_signal == "bullish":
            bull_score += 15
            bear_score -= 5
        elif macd_signal == "bearish":
            bear_score += 15
            bull_score -= 5

        # MA 정렬 기여 (최대 ±15점)
        if ma_alignment == "bullish":
            bull_score += 15
            bear_score -= 10
        elif ma_alignment == "bearish":
            bear_score += 15
            bull_score -= 10

        # 추세 방향 기여 (최대 ±10점)
        if trend_direction == "up":
            bull_score += 10
        elif trend_direction == "down":
            bear_score += 10

        # 거래량 추세 기여 (최대 ±5점)
        if volume_trend == "increasing":
            # 현재 추세 방향 강화
            if trend_direction == "up":
                bull_score += 5
            elif trend_direction == "down":
                bear_score += 5

        # 0~100 범위로 클램핑
        bull_score = max(0, min(100, bull_score))
        bear_score = max(0, min(100, bear_score))

        return bull_score, bear_score

    def _recommend_strategy(
        self,
        regime: MarketRegime,
        trend_dir: str,
        trend_str: TrendStrength,
        bull_score: float,
        bear_score: float,
        price: float,
        support: float,
        resistance: float,
        vol_regime: str
    ) -> Tuple[str, list]:
        """최적 전략 추천"""

        reasoning = []

        # 고변동성/극한 변동성 시장
        if regime == MarketRegime.HIGH_VOLATILITY or vol_regime == "extreme":
            reasoning.append("⚠️ 고변동성 시장 - 포지션 축소 또는 관망 권장")
            reasoning.append(f"   변동성: {vol_regime}")
            return "wait", reasoning

        # 추세 불분명
        if trend_str in [TrendStrength.WEAK, TrendStrength.NO_TREND]:
            reasoning.append("⏸️ 추세 불분명 - 명확한 방향 확인까지 대기")
            reasoning.append(f"   추세 강도: {trend_str.value}")
            reasoning.append(f"   매수 점수: {bull_score:.0f}, 매도 점수: {bear_score:.0f}")
            return "wait", reasoning

        # 명확한 상승 추세 + 높은 매수 점수
        if trend_dir == "up" and bull_score > 60:
            reasoning.append(f"✅ 상승 추세 확인 (강도: {trend_str.value})")
            reasoning.append(f"✅ 매수 유리 점수: {bull_score:.0f}/100")

            # 지지선 근처면 더 좋음
            dist_to_support = ((price - support) / price) * 100 if price > 0 else 100
            if dist_to_support < 3:
                reasoning.append(f"✅ 지지선 근처 ({dist_to_support:.1f}% 위)")
            else:
                reasoning.append(f"ℹ️ 지지선까지 {dist_to_support:.1f}% - 눌림목 대기 고려")

            return "long", reasoning

        # 명확한 하락 추세 + 높은 매도 점수
        if trend_dir == "down" and bear_score > 60:
            reasoning.append(f"✅ 하락 추세 확인 (강도: {trend_str.value})")
            reasoning.append(f"✅ 매도 유리 점수: {bear_score:.0f}/100")

            dist_to_resistance = ((resistance - price) / price) * 100 if price > 0 else 100
            if dist_to_resistance < 3:
                reasoning.append(f"✅ 저항선 근처 ({dist_to_resistance:.1f}% 아래)")

            return "short", reasoning

        # 점수 차이가 크면 해당 방향
        if bull_score - bear_score > 20:
            reasoning.append(f"📈 매수 우위 (점수 차: {bull_score - bear_score:.0f})")
            return "long", reasoning

        if bear_score - bull_score > 20:
            reasoning.append(f"📉 매도 우위 (점수 차: {bear_score - bull_score:.0f})")
            return "short", reasoning

        # 기본값: 대기
        reasoning.append("ℹ️ 조건 불충족 - 더 좋은 기회 대기")
        reasoning.append(f"   매수 점수: {bull_score:.0f}, 매도 점수: {bear_score:.0f}")
        return "wait", reasoning


if __name__ == "__main__":
    import random

    # 테스트용 더미 데이터 생성
    dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
    base_price = 100_000_000  # 1억

    prices = [base_price]
    for _ in range(99):
        change = random.uniform(-0.02, 0.025)  # 약간 상승 편향
        prices.append(prices[-1] * (1 + change))

    df = pd.DataFrame({
        'timestamp': dates,
        'open': [p * random.uniform(0.998, 1.002) for p in prices],
        'high': [p * random.uniform(1.001, 1.02) for p in prices],
        'low': [p * random.uniform(0.98, 0.999) for p in prices],
        'close': prices,
        'volume': [random.uniform(1000, 10000) for _ in prices],
    })

    analyzer = MarketAnalyzer()
    context = analyzer.analyze(df, "BTC/KRW")

    print("=== 시장 분석 결과 ===")
    print(f"시장 국면: {context.regime.value}")
    print(f"추세 방향: {context.trend_direction}")
    print(f"추세 강도: {context.trend_strength.value}")
    print(f"RSI: {context.rsi} ({context.rsi_signal})")
    print(f"MACD: {context.macd_signal}")
    print(f"MA 정렬: {context.ma_alignment}")
    print(f"지지선: {context.nearest_support:,.0f}원 (현재가 대비 {context.distance_to_support_pct:.1f}%)")
    print(f"저항선: {context.nearest_resistance:,.0f}원 (현재가 대비 {context.distance_to_resistance_pct:.1f}%)")
    print(f"변동성: {context.volatility_regime} (ATR {context.atr_percent:.2f}%)")
    print(f"매수 점수: {context.bullish_score:.0f}/100")
    print(f"매도 점수: {context.bearish_score:.0f}/100")
    print(f"추천 전략: {context.recommended_strategy}")
    print(f"근거: {context.reasoning}")
