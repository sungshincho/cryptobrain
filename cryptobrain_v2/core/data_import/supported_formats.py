"""
CryptoBrain V2 - 거래소별 CSV 포맷 정의
각 거래소의 CSV 컬럼 매핑 및 데이터 변환 규칙
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
from enum import Enum


class TradeType(Enum):
    """거래 유형"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class ExchangeFormat:
    """거래소 CSV 포맷 정의"""
    name: str
    display_name: str
    encoding: str
    date_format: str
    column_mapping: Dict[str, str]  # 표준 필드 -> 거래소 컬럼명
    trade_type_mapping: Dict[str, TradeType]  # 거래소 값 -> TradeType
    skip_rows: int = 0
    decimal_separator: str = "."
    thousands_separator: str = ","
    notes: str = ""


# 표준 필드 정의
STANDARD_FIELDS = [
    "timestamp",      # 거래 시각
    "trade_type",     # 매수/매도
    "symbol",         # 거래 종목 (BTC, ETH 등)
    "market",         # 마켓 (KRW, BTC 등)
    "quantity",       # 거래 수량
    "price",          # 거래 단가
    "total_amount",   # 총 거래금액
    "fee",            # 수수료
    "order_id",       # 주문 ID (선택)
]


# 업비트 CSV 포맷
UPBIT_FORMAT = ExchangeFormat(
    name="upbit",
    display_name="업비트 (Upbit)",
    encoding="utf-8-sig",  # 업비트는 BOM 포함 UTF-8
    date_format="%Y-%m-%d %H:%M:%S",
    column_mapping={
        "timestamp": "일시",
        "trade_type": "종류",
        "symbol": "마켓",  # KRW-BTC 형태, 파싱 필요
        "market": "마켓",
        "quantity": "거래수량",
        "price": "거래단가",
        "total_amount": "거래금액",
        "fee": "수수료",
        "order_id": "주문번호",
    },
    trade_type_mapping={
        "매수": TradeType.BUY,
        "매도": TradeType.SELL,
    },
    skip_rows=0,
    notes="업비트 > 마이페이지 > 거래내역 > 전체 내역 > CSV 다운로드"
)


# 빗썸 CSV 포맷 (Phase 2 예정)
BITHUMB_FORMAT = ExchangeFormat(
    name="bithumb",
    display_name="빗썸 (Bithumb)",
    encoding="euc-kr",
    date_format="%Y-%m-%d %H:%M:%S",
    column_mapping={
        "timestamp": "거래일시",
        "trade_type": "거래종류",
        "symbol": "거래통화",
        "market": "결제통화",
        "quantity": "거래수량",
        "price": "거래단가",
        "total_amount": "거래금액",
        "fee": "수수료",
        "order_id": "주문번호",
    },
    trade_type_mapping={
        "매수": TradeType.BUY,
        "매도": TradeType.SELL,
    },
    skip_rows=0,
    notes="빗썸 > 마이페이지 > 거래내역 > 엑셀 다운로드"
)


# 코인원 CSV 포맷 (Phase 2 예정)
COINONE_FORMAT = ExchangeFormat(
    name="coinone",
    display_name="코인원 (Coinone)",
    encoding="utf-8",
    date_format="%Y-%m-%d %H:%M:%S",
    column_mapping={
        "timestamp": "체결시각",
        "trade_type": "주문유형",
        "symbol": "코인",
        "market": "마켓",
        "quantity": "체결수량",
        "price": "체결가격",
        "total_amount": "체결금액",
        "fee": "수수료",
        "order_id": "주문번호",
    },
    trade_type_mapping={
        "BUY": TradeType.BUY,
        "SELL": TradeType.SELL,
        "매수": TradeType.BUY,
        "매도": TradeType.SELL,
    },
    skip_rows=0,
    notes="코인원 > 마이페이지 > 거래내역 > 다운로드"
)


# 지원 거래소 목록
EXCHANGE_FORMATS: Dict[str, ExchangeFormat] = {
    "upbit": UPBIT_FORMAT,
    "bithumb": BITHUMB_FORMAT,
    "coinone": COINONE_FORMAT,
}


def get_supported_exchanges() -> List[Dict[str, str]]:
    """지원 거래소 목록 반환"""
    return [
        {
            "name": fmt.name,
            "display_name": fmt.display_name,
            "notes": fmt.notes,
        }
        for fmt in EXCHANGE_FORMATS.values()
    ]


def get_exchange_format(exchange_name: str) -> Optional[ExchangeFormat]:
    """거래소명으로 포맷 정보 반환"""
    return EXCHANGE_FORMATS.get(exchange_name.lower())
