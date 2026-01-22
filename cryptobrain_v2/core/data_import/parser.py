"""
CryptoBrain V2 - 거래 데이터 파서
거래소 CSV 파일을 통합 포맷으로 변환하고 FIFO 손익 계산
"""
import pandas as pd
import io
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass, field
from collections import defaultdict
import re

from .supported_formats import (
    ExchangeFormat,
    TradeType,
    EXCHANGE_FORMATS,
    get_exchange_format,
)


@dataclass
class ParsedTrade:
    """파싱된 거래 데이터"""
    timestamp: datetime
    trade_type: TradeType
    symbol: str  # BTC, ETH 등
    market: str  # KRW, BTC 등
    quantity: float
    price: float
    total_amount: float
    fee: float
    order_id: Optional[str] = None
    exchange: str = ""

    # FIFO 계산 후 채워지는 필드
    realized_pnl: Optional[float] = None
    avg_buy_price: Optional[float] = None

    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "trade_type": self.trade_type.value,
            "symbol": self.symbol,
            "market": self.market,
            "quantity": self.quantity,
            "price": self.price,
            "total_amount": self.total_amount,
            "fee": self.fee,
            "order_id": self.order_id,
            "exchange": self.exchange,
            "realized_pnl": self.realized_pnl,
            "avg_buy_price": self.avg_buy_price,
        }


@dataclass
class ImportResult:
    """임포트 결과"""
    success: bool
    total_rows: int = 0
    parsed_rows: int = 0
    skipped_rows: int = 0
    trades: List[ParsedTrade] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # 요약 통계
    total_buy_amount: float = 0
    total_sell_amount: float = 0
    total_fee: float = 0
    symbols_traded: List[str] = field(default_factory=list)
    date_range: Tuple[Optional[datetime], Optional[datetime]] = (None, None)


@dataclass
class FIFOPosition:
    """FIFO 계산용 포지션"""
    quantity: float
    price: float
    timestamp: datetime
    fee: float = 0


class DataImporter:
    """거래 데이터 임포터"""

    def __init__(self, exchange: str = "upbit"):
        """
        초기화

        Args:
            exchange: 거래소명 (upbit, bithumb, coinone 등)
        """
        self.exchange = exchange.lower()
        self.format = get_exchange_format(self.exchange)

        if not self.format:
            raise ValueError(f"지원하지 않는 거래소입니다: {exchange}")

    def parse_csv(
        self,
        file_content: Union[str, bytes, io.BytesIO],
        validate: bool = True
    ) -> ImportResult:
        """
        CSV 파일 파싱

        Args:
            file_content: CSV 파일 내용 (문자열, 바이트, 또는 BytesIO)
            validate: 데이터 검증 여부

        Returns:
            ImportResult: 파싱 결과
        """
        result = ImportResult(success=False)

        try:
            # DataFrame으로 로드
            df = self._load_csv(file_content)
            result.total_rows = len(df)

            if df.empty:
                result.errors.append("CSV 파일이 비어있습니다")
                return result

            # 컬럼 검증
            missing_cols = self._validate_columns(df)
            if missing_cols:
                result.errors.append(f"필수 컬럼이 없습니다: {', '.join(missing_cols)}")
                return result

            # 각 행 파싱
            trades = []
            for idx, row in df.iterrows():
                try:
                    trade = self._parse_row(row)
                    if trade:
                        trades.append(trade)
                        result.parsed_rows += 1
                    else:
                        result.skipped_rows += 1
                except Exception as e:
                    result.skipped_rows += 1
                    result.warnings.append(f"행 {idx + 1} 파싱 실패: {str(e)}")

            # 시간순 정렬
            trades.sort(key=lambda t: t.timestamp)
            result.trades = trades

            # 요약 통계 계산
            self._calculate_summary(result)

            result.success = True

        except Exception as e:
            result.errors.append(f"CSV 파싱 오류: {str(e)}")

        return result

    def _load_csv(self, file_content: Union[str, bytes, io.BytesIO]) -> pd.DataFrame:
        """CSV 파일을 DataFrame으로 로드"""
        encoding = self.format.encoding
        skip_rows = self.format.skip_rows

        if isinstance(file_content, bytes):
            file_content = io.BytesIO(file_content)
        elif isinstance(file_content, str):
            # 문자열인 경우 바이트로 변환
            file_content = io.BytesIO(file_content.encode(encoding))

        try:
            df = pd.read_csv(
                file_content,
                encoding=encoding,
                skiprows=skip_rows,
            )
        except UnicodeDecodeError:
            # 인코딩 실패 시 다른 인코딩 시도
            file_content.seek(0)
            for alt_encoding in ["utf-8", "utf-8-sig", "euc-kr", "cp949"]:
                try:
                    df = pd.read_csv(
                        file_content,
                        encoding=alt_encoding,
                        skiprows=skip_rows,
                    )
                    break
                except:
                    file_content.seek(0)
                    continue
            else:
                raise ValueError("CSV 인코딩을 확인할 수 없습니다")

        return df

    def _validate_columns(self, df: pd.DataFrame) -> List[str]:
        """필수 컬럼 검증"""
        required_standard_fields = ["timestamp", "trade_type", "quantity", "price"]
        missing = []

        for field in required_standard_fields:
            col_name = self.format.column_mapping.get(field)
            if col_name and col_name not in df.columns:
                missing.append(col_name)

        return missing

    def _parse_row(self, row: pd.Series) -> Optional[ParsedTrade]:
        """단일 행 파싱"""
        mapping = self.format.column_mapping

        # 거래 유형 파싱
        trade_type_raw = str(row.get(mapping["trade_type"], "")).strip()
        trade_type = self.format.trade_type_mapping.get(trade_type_raw)

        if not trade_type:
            # 매수/매도가 아닌 행 (입금, 출금 등) 스킵
            return None

        # 종목 및 마켓 파싱 (업비트: KRW-BTC 형식)
        market_raw = str(row.get(mapping["symbol"], "")).strip()
        symbol, market = self._parse_symbol(market_raw)

        if not symbol:
            return None

        # 타임스탬프 파싱
        timestamp_raw = row.get(mapping["timestamp"])
        timestamp = self._parse_timestamp(timestamp_raw)

        # 숫자 필드 파싱
        quantity = self._parse_number(row.get(mapping["quantity"], 0))
        price = self._parse_number(row.get(mapping["price"], 0))
        total_amount = self._parse_number(row.get(mapping["total_amount"], 0))
        fee = self._parse_number(row.get(mapping.get("fee", ""), 0))

        # 주문 ID (선택)
        order_id = str(row.get(mapping.get("order_id", ""), "")) or None

        return ParsedTrade(
            timestamp=timestamp,
            trade_type=trade_type,
            symbol=symbol,
            market=market,
            quantity=quantity,
            price=price,
            total_amount=total_amount,
            fee=fee,
            order_id=order_id,
            exchange=self.exchange,
        )

    def _parse_symbol(self, market_raw: str) -> Tuple[str, str]:
        """
        마켓 문자열에서 심볼과 마켓 추출

        업비트: KRW-BTC -> (BTC, KRW)
        """
        if "-" in market_raw:
            parts = market_raw.split("-")
            if len(parts) == 2:
                return parts[1], parts[0]  # 심볼, 마켓

        # 단순 심볼인 경우
        return market_raw, "KRW"

    def _parse_timestamp(self, timestamp_raw) -> datetime:
        """타임스탬프 파싱"""
        if pd.isna(timestamp_raw):
            return datetime.now()

        timestamp_str = str(timestamp_raw).strip()

        # 다양한 포맷 시도
        formats = [
            self.format.date_format,
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y.%m.%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue

        # 기본값
        return datetime.now()

    def _parse_number(self, value) -> float:
        """숫자 파싱 (천단위 구분자 처리)"""
        if pd.isna(value):
            return 0.0

        if isinstance(value, (int, float)):
            return float(value)

        # 문자열 처리
        value_str = str(value).strip()

        # 천단위 구분자 제거
        value_str = value_str.replace(self.format.thousands_separator, "")

        # 소수점 변환
        if self.format.decimal_separator != ".":
            value_str = value_str.replace(self.format.decimal_separator, ".")

        # 통화 기호 등 제거
        value_str = re.sub(r"[^\d.\-]", "", value_str)

        try:
            return float(value_str) if value_str else 0.0
        except ValueError:
            return 0.0

    def _calculate_summary(self, result: ImportResult):
        """요약 통계 계산"""
        if not result.trades:
            return

        symbols = set()
        min_date = None
        max_date = None

        for trade in result.trades:
            symbols.add(trade.symbol)

            if trade.trade_type == TradeType.BUY:
                result.total_buy_amount += trade.total_amount
            else:
                result.total_sell_amount += trade.total_amount

            result.total_fee += trade.fee

            if min_date is None or trade.timestamp < min_date:
                min_date = trade.timestamp
            if max_date is None or trade.timestamp > max_date:
                max_date = trade.timestamp

        result.symbols_traded = sorted(list(symbols))
        result.date_range = (min_date, max_date)

    def calculate_fifo_pnl(
        self,
        trades: List[ParsedTrade],
        include_fees: bool = True
    ) -> Tuple[List[ParsedTrade], Dict[str, Dict]]:
        """
        FIFO 방식으로 실현 손익 계산

        Args:
            trades: 파싱된 거래 목록 (시간순 정렬 필요)
            include_fees: 수수료 포함 여부

        Returns:
            (업데이트된 거래 목록, 종목별 통계)
        """
        # 종목별 포지션 큐 (FIFO)
        positions: Dict[str, List[FIFOPosition]] = defaultdict(list)

        # 종목별 통계
        symbol_stats: Dict[str, Dict] = defaultdict(lambda: {
            "total_buy_quantity": 0,
            "total_buy_amount": 0,
            "total_sell_quantity": 0,
            "total_sell_amount": 0,
            "total_fee": 0,
            "realized_pnl": 0,
            "current_quantity": 0,
            "avg_buy_price": 0,
        })

        for trade in trades:
            symbol = trade.symbol
            stats = symbol_stats[symbol]

            if trade.trade_type == TradeType.BUY:
                # 매수: 포지션 추가
                positions[symbol].append(FIFOPosition(
                    quantity=trade.quantity,
                    price=trade.price,
                    timestamp=trade.timestamp,
                    fee=trade.fee if include_fees else 0,
                ))

                stats["total_buy_quantity"] += trade.quantity
                stats["total_buy_amount"] += trade.total_amount
                stats["total_fee"] += trade.fee

                # 평균 매수가 계산
                total_qty = sum(p.quantity for p in positions[symbol])
                total_cost = sum(p.quantity * p.price for p in positions[symbol])
                stats["avg_buy_price"] = total_cost / total_qty if total_qty > 0 else 0
                stats["current_quantity"] = total_qty

                trade.avg_buy_price = stats["avg_buy_price"]

            else:  # SELL
                # 매도: FIFO 방식으로 손익 계산
                remaining_qty = trade.quantity
                realized_pnl = 0
                cost_basis = 0

                while remaining_qty > 0 and positions[symbol]:
                    pos = positions[symbol][0]

                    if pos.quantity <= remaining_qty:
                        # 포지션 전량 소진
                        cost_basis += pos.quantity * pos.price
                        if include_fees:
                            cost_basis += pos.fee
                        remaining_qty -= pos.quantity
                        positions[symbol].pop(0)
                    else:
                        # 포지션 일부 소진
                        cost_basis += remaining_qty * pos.price
                        if include_fees:
                            cost_basis += pos.fee * (remaining_qty / pos.quantity)
                        pos.quantity -= remaining_qty
                        pos.fee -= pos.fee * (remaining_qty / pos.quantity) if include_fees else 0
                        remaining_qty = 0

                # 실현 손익 계산
                sell_proceeds = trade.total_amount
                if include_fees:
                    sell_proceeds -= trade.fee

                realized_pnl = sell_proceeds - cost_basis

                trade.realized_pnl = realized_pnl
                stats["total_sell_quantity"] += trade.quantity
                stats["total_sell_amount"] += trade.total_amount
                stats["total_fee"] += trade.fee
                stats["realized_pnl"] += realized_pnl

                # 현재 보유량 및 평균가 업데이트
                total_qty = sum(p.quantity for p in positions[symbol])
                total_cost = sum(p.quantity * p.price for p in positions[symbol])
                stats["current_quantity"] = total_qty
                stats["avg_buy_price"] = total_cost / total_qty if total_qty > 0 else 0

                trade.avg_buy_price = stats["avg_buy_price"]

        return trades, dict(symbol_stats)

    def to_dataframe(self, trades: List[ParsedTrade]) -> pd.DataFrame:
        """거래 목록을 DataFrame으로 변환"""
        if not trades:
            return pd.DataFrame()

        data = [trade.to_dict() for trade in trades]
        df = pd.DataFrame(data)

        # 컬럼 순서 정리
        columns = [
            "timestamp", "trade_type", "symbol", "market",
            "quantity", "price", "total_amount", "fee",
            "realized_pnl", "avg_buy_price", "exchange", "order_id"
        ]

        df = df[[c for c in columns if c in df.columns]]

        return df


def import_upbit_csv(
    file_content: Union[str, bytes, io.BytesIO],
    calculate_pnl: bool = True
) -> ImportResult:
    """
    업비트 CSV 간편 임포트 함수

    Args:
        file_content: CSV 파일 내용
        calculate_pnl: FIFO 손익 계산 여부

    Returns:
        ImportResult: 임포트 결과
    """
    importer = DataImporter("upbit")
    result = importer.parse_csv(file_content)

    if result.success and calculate_pnl and result.trades:
        result.trades, _ = importer.calculate_fifo_pnl(result.trades)

    return result
