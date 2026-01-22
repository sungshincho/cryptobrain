"""
CryptoBrain V2 - 시세 데이터 수집 모듈
업비트/바이낸스 API를 통한 OHLCV 데이터 수집
"""
import ccxt
import pandas as pd
from datetime import datetime
from typing import Optional
import time

from ..config.settings import (
    DEFAULT_EXCHANGE,
    DEFAULT_COINS,
    TIMEFRAMES,
)


class DataFetcher:
    """거래소 시세 데이터 수집기"""

    def __init__(self, exchange: str = DEFAULT_EXCHANGE):
        """
        Args:
            exchange: 거래소 이름 (upbit, binance)
        """
        self.exchange_name = exchange
        self.exchange = self._init_exchange(exchange)
        self._cache = {}
        self._cache_time = {}
        self._cache_ttl = 60  # 캐시 유효 시간 (초)

    def _init_exchange(self, exchange: str) -> ccxt.Exchange:
        """거래소 객체 초기화"""
        exchange_map = {
            "upbit": ccxt.upbit,
            "binance": ccxt.binance,
        }

        if exchange not in exchange_map:
            raise ValueError(f"지원하지 않는 거래소: {exchange}")

        return exchange_map[exchange]({
            "enableRateLimit": True,
        })

    def _get_cache_key(self, symbol: str, timeframe: str) -> str:
        """캐시 키 생성"""
        return f"{symbol}_{timeframe}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """캐시 유효성 검사"""
        if cache_key not in self._cache_time:
            return False
        elapsed = time.time() - self._cache_time[cache_key]
        return elapsed < self._cache_ttl

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> pd.DataFrame:
        """
        OHLCV 데이터 조회

        Args:
            symbol: 심볼 (예: "BTC/KRW")
            timeframe: 타임프레임 ("1h", "4h", "1d")
            limit: 조회할 캔들 수

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        cache_key = self._get_cache_key(symbol, timeframe)

        # 캐시 확인
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key].copy()

        try:
            ohlcv = self.exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                limit=limit
            )

            df = pd.DataFrame(
                ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df["symbol"] = symbol

            # 캐시 저장
            self._cache[cache_key] = df
            self._cache_time[cache_key] = time.time()

            return df.copy()

        except Exception as e:
            print(f"OHLCV 조회 실패 ({symbol}, {timeframe}): {e}")
            return pd.DataFrame()

    def get_multi_timeframe(self, symbol: str) -> dict[str, pd.DataFrame]:
        """
        멀티 타임프레임 데이터 조회

        Args:
            symbol: 심볼 (예: "BTC/KRW")

        Returns:
            {timeframe: DataFrame} 딕셔너리
        """
        result = {}

        for tf, config in TIMEFRAMES.items():
            df = self.get_ohlcv(symbol, tf, config["limit"])
            if not df.empty:
                result[tf] = df

        return result

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        현재가 조회

        Args:
            symbol: 심볼 (예: "BTC/KRW")

        Returns:
            현재가 또는 None
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker.get("last") or ticker.get("close")
        except Exception as e:
            print(f"현재가 조회 실패 ({symbol}): {e}")
            return None

    def get_ticker(self, symbol: str) -> dict:
        """
        티커 정보 조회

        Args:
            symbol: 심볼 (예: "BTC/KRW")

        Returns:
            티커 정보 딕셔너리
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                "symbol": symbol,
                "last": ticker.get("last"),
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
                "high": ticker.get("high"),
                "low": ticker.get("low"),
                "volume": ticker.get("baseVolume"),
                "change": ticker.get("percentage"),
                "timestamp": ticker.get("timestamp"),
            }
        except Exception as e:
            print(f"티커 조회 실패 ({symbol}): {e}")
            return {}

    def get_all_watched_coins(
        self,
        coins: Optional[list[str]] = None
    ) -> dict[str, dict]:
        """
        관심 코인 전체 데이터 조회

        Args:
            coins: 코인 심볼 리스트 (기본: DEFAULT_COINS)

        Returns:
            {symbol: {price, rsi, trend, volume, ...}} 딕셔너리
        """
        if coins is None:
            coins = DEFAULT_COINS

        result = {}

        for symbol in coins:
            try:
                # 1시간봉 데이터로 기본 정보 계산
                df = self.get_ohlcv(symbol, "1h", 30)

                if df.empty:
                    continue

                # 기본 지표 계산
                df["MA20"] = df["close"].rolling(20).mean()
                delta = df["close"].diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                df["RSI"] = 100 - (100 / (1 + rs))

                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else latest

                # 변동률 계산
                change = ((latest["close"] - prev["close"]) / prev["close"]) * 100

                result[symbol] = {
                    "price": latest["close"],
                    "open": latest["open"],
                    "high": latest["high"],
                    "low": latest["low"],
                    "volume": latest["volume"],
                    "rsi": latest["RSI"] if pd.notna(latest["RSI"]) else 50,
                    "ma20": latest["MA20"] if pd.notna(latest["MA20"]) else latest["close"],
                    "trend": "bullish" if latest["close"] > latest["MA20"] else "bearish",
                    "change": change,
                    "timestamp": latest["timestamp"],
                }

            except Exception as e:
                print(f"코인 데이터 조회 실패 ({symbol}): {e}")
                continue

        return result

    def get_market_summary(self, coins: Optional[list[str]] = None) -> dict:
        """
        시장 요약 정보

        Args:
            coins: 코인 심볼 리스트

        Returns:
            시장 요약 딕셔너리
        """
        data = self.get_all_watched_coins(coins)

        if not data:
            return {
                "total_coins": 0,
                "bullish_count": 0,
                "bearish_count": 0,
                "market_sentiment": "neutral",
                "oversold_coins": [],
                "overbought_coins": [],
            }

        bullish = sum(1 for d in data.values() if d["trend"] == "bullish")
        bearish = sum(1 for d in data.values() if d["trend"] == "bearish")
        oversold = [s for s, d in data.items() if d["rsi"] < 30]
        overbought = [s for s, d in data.items() if d["rsi"] > 70]

        # 시장 심리 판단
        total = len(data)
        if bullish / total > 0.7:
            sentiment = "very_bullish"
        elif bullish / total > 0.5:
            sentiment = "bullish"
        elif bearish / total > 0.7:
            sentiment = "very_bearish"
        elif bearish / total > 0.5:
            sentiment = "bearish"
        else:
            sentiment = "neutral"

        return {
            "total_coins": total,
            "bullish_count": bullish,
            "bearish_count": bearish,
            "market_sentiment": sentiment,
            "oversold_coins": oversold,
            "overbought_coins": overbought,
            "data": data,
        }

    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()
        self._cache_time.clear()


if __name__ == "__main__":
    # 테스트
    fetcher = DataFetcher("upbit")

    print("=== 현재가 조회 ===")
    price = fetcher.get_current_price("BTC/KRW")
    print(f"BTC/KRW: {price:,.0f}원" if price else "조회 실패")

    print("\n=== OHLCV 데이터 ===")
    df = fetcher.get_ohlcv("BTC/KRW", "1h", 10)
    if not df.empty:
        print(df.tail(3).to_string())

    print("\n=== 멀티 타임프레임 ===")
    mtf = fetcher.get_multi_timeframe("BTC/KRW")
    for tf, data in mtf.items():
        print(f"{tf}: {len(data)} candles")

    print("\n=== 관심 코인 전체 ===")
    watched = fetcher.get_all_watched_coins(["BTC/KRW", "ETH/KRW"])
    for sym, info in watched.items():
        print(f"{sym}: {info['price']:,.0f}원 (RSI: {info['rsi']:.1f}, {info['trend']})")

    print("\n=== 시장 요약 ===")
    summary = fetcher.get_market_summary()
    print(f"시장 심리: {summary['market_sentiment']}")
    print(f"상승: {summary['bullish_count']}, 하락: {summary['bearish_count']}")
