"""
CryptoBrain V3 - 감정 필터

사용자의 감정적 요청을 필터링하고 이성적 판단으로 유도
FOMO, 공포, 복수매매, 과잉확신 등을 감지하고 차단

핵심 원칙: 감정적 거래는 손실의 원인
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
import re


@dataclass
class EmotionAnalysis:
    """사용자 요청의 감정 분석 결과"""
    detected_emotions: list           # ["fomo", "fear", "greed", "revenge"]
    emotion_score: float              # 0~1 (높을수록 감정적)
    is_rational: bool                 # 이성적 요청인가
    warnings: list                    # 경고 메시지
    should_block: bool                # 요청 차단 여부
    alternative_advice: str           # 대안 조언
    emotion_details: dict = field(default_factory=dict)  # 감정별 상세 점수

    def to_dict(self) -> dict:
        return {
            "detected_emotions": self.detected_emotions,
            "emotion_score": self.emotion_score,
            "is_rational": self.is_rational,
            "warnings": self.warnings,
            "should_block": self.should_block,
            "alternative_advice": self.alternative_advice,
            "emotion_details": self.emotion_details,
        }


class EmotionFilter:
    """
    사용자의 감정적 요청을 필터링하고 이성적 판단으로 유도

    탐지 대상:
    1. FOMO (Fear of Missing Out) - 급등 후 매수 충동
    2. 공포 매도 - 급락 시 손절 충동
    3. 복수 매매 - 손실 후 즉시 재진입
    4. 과잉 확신 - 올인, 레버리지 과다
    5. 매몰 비용 - 물타기 집착
    6. 탐욕 - 무리한 수익 추구
    """

    # FOMO 패턴 (Fear of Missing Out)
    FOMO_PATTERNS = [
        r"지금 안 사면",
        r"놓치",
        r"늦기 전에",
        r"다들 사",
        r"급등",
        r"폭등",
        r"더 오르기 전에",
        r"올라가는데",
        r"달리는데",
        r"펌핑",
        r"미친듯이 오르",
        r"지금 들어가야",
        r"기회를 놓",
        r"빨리 사",
        r"얼른 사",
        r"지금이 마지막",
        r"못 타",
        r"뒤늦게",
    ]

    # 공포 패턴
    FEAR_PATTERNS = [
        r"폭락",
        r"급락",
        r"망했",
        r"다 팔아",
        r"전부 정리",
        r"더 떨어지기 전에",
        r"물렸",
        r"어떡해",
        r"손절해야",
        r"다 날아가",
        r"끝났",
        r"바닥이 없",
        r"무섭",
        r"공포",
        r"패닉",
        r"지옥",
        r"나락",
    ]

    # 복수 매매 패턴
    REVENGE_PATTERNS = [
        r"복구",
        r"원금 회복",
        r"만회",
        r"본전",
        r"다시 들어가",
        r"손실 메꾸",
        r"잃은 거 되찾",
        r"방금 손절.*다시",
        r"털리.*재진입",
        r"원금으로",
        r"찾아야",
    ]

    # 과잉 확신 패턴
    OVERCONFIDENCE_PATTERNS = [
        r"올인",
        r"전재산",
        r"몰빵",
        r"레버리지",
        r"10배",
        r"20배",
        r"100배",
        r"확실",
        r"무조건",
        r"절대",
        r"100%",
        r"반드시",
        r"틀림없",
        r"무조건 오른다",
        r"무조건 간다",
    ]

    # 탐욕 패턴
    GREED_PATTERNS = [
        r"10배",
        r"100배",
        r"대박",
        r"한방",
        r"인생역전",
        r"부자",
        r"떡상",
        r"달나라",
        r"억만장자",
        r"x100",
        r"x10",
        r"로또",
    ]

    # 물타기/매몰비용 패턴
    SUNK_COST_PATTERNS = [
        r"물타기",
        r"추가 매수.*-",
        r"평단.*낮추",
        r"물렸는데.*더 사",
        r"손실.*추가",
        r"평균 단가",
        r"비중 늘",
    ]

    def __init__(self, user_trade_history: list = None):
        """
        Args:
            user_trade_history: 사용자의 최근 거래 기록
        """
        self.history = user_trade_history or []

    def analyze_request(
        self,
        user_message: str,
        recent_market_move: dict = None,
        last_trade_result: dict = None,
        time_since_last_trade: timedelta = None
    ) -> EmotionAnalysis:
        """
        사용자 요청의 감정 분석

        Args:
            user_message: 사용자 입력 메시지
            recent_market_move: 최근 시장 움직임 {"change_24h": float, "direction": str}
            last_trade_result: 마지막 거래 결과 {"pnl": float, "pnl_pct": float}
            time_since_last_trade: 마지막 거래 후 경과 시간

        Returns:
            EmotionAnalysis: 감정 분석 결과
        """
        detected = []
        warnings = []
        emotion_details = {}
        total_score = 0

        message_lower = user_message.lower()

        # 1. FOMO 감지
        fomo_score = self._detect_pattern(message_lower, self.FOMO_PATTERNS)
        if fomo_score > 0:
            detected.append("fomo")
            emotion_details["fomo"] = fomo_score
            total_score += fomo_score * 0.25

            # 최근 급등 확인으로 FOMO 강화
            if recent_market_move and recent_market_move.get('change_24h', 0) > 10:
                change = recent_market_move['change_24h']
                warnings.append(
                    f"🚨 FOMO 감지: 이미 24시간 동안 {change:.1f}% 상승했습니다. "
                    f"고점 매수 위험이 매우 높습니다."
                )
                total_score += 0.2
            elif recent_market_move and recent_market_move.get('change_24h', 0) > 5:
                warnings.append(
                    f"⚠️ FOMO 주의: 최근 급등 후 진입은 위험합니다. "
                    f"조정을 기다리세요."
                )

        # 2. 공포 감지
        fear_score = self._detect_pattern(message_lower, self.FEAR_PATTERNS)
        if fear_score > 0:
            detected.append("fear")
            emotion_details["fear"] = fear_score
            total_score += fear_score * 0.25

            warnings.append(
                "🚨 공포 매도 감지: 급락 시 패닉셀은 최악의 타이밍인 경우가 많습니다. "
                "원래 계획했던 손절가를 확인하세요."
            )

            # 급락 중이면 추가 경고
            if recent_market_move and recent_market_move.get('change_24h', 0) < -10:
                warnings.append(
                    f"   실제로 {abs(recent_market_move['change_24h']):.1f}% 하락 중이지만, "
                    f"바닥에서 매도하면 손실이 확정됩니다."
                )

        # 3. 복수 매매 감지
        revenge_score = self._detect_pattern(message_lower, self.REVENGE_PATTERNS)
        if revenge_score > 0:
            detected.append("revenge")
            emotion_details["revenge"] = revenge_score
            total_score += revenge_score * 0.30

            # 최근 손실 확인
            if last_trade_result and last_trade_result.get('pnl', 0) < 0:
                pnl = last_trade_result.get('pnl_pct', last_trade_result.get('pnl', 0))
                warnings.append(
                    f"🚨 복수 매매 감지: 직전 거래에서 {abs(pnl):.1f}% 손실이 있었습니다. "
                    f"감정적 재진입은 손실을 키울 수 있습니다."
                )
                total_score += 0.25

            # 시간 체크
            if time_since_last_trade and time_since_last_trade < timedelta(hours=4):
                hours = time_since_last_trade.total_seconds() / 3600
                warnings.append(
                    f"   마지막 거래 후 {hours:.1f}시간밖에 지나지 않았습니다. "
                    f"최소 4시간 후에 다시 검토하세요."
                )
                total_score += 0.1

        # 4. 과잉 확신 감지
        overconf_score = self._detect_pattern(message_lower, self.OVERCONFIDENCE_PATTERNS)
        if overconf_score > 0:
            detected.append("overconfidence")
            emotion_details["overconfidence"] = overconf_score
            total_score += overconf_score * 0.35

            warnings.append(
                "🚨 과잉 확신 감지: '확실한' 거래는 없습니다. "
                "자본의 2% 이상 리스크는 절대 권장하지 않습니다."
            )

            # 레버리지 언급
            if re.search(r"(레버리지|10배|20배|100배)", message_lower):
                warnings.append(
                    "   ⛔ 레버리지는 손실을 극대화합니다. "
                    "전문가도 레버리지로 파산합니다."
                )
                total_score += 0.2

        # 5. 탐욕 감지
        greed_score = self._detect_pattern(message_lower, self.GREED_PATTERNS)
        if greed_score > 0:
            detected.append("greed")
            emotion_details["greed"] = greed_score
            total_score += greed_score * 0.20

            warnings.append(
                "⚠️ 탐욕 감지: 비현실적 수익 기대는 과도한 리스크로 이어집니다. "
                "현실적인 목표(월 3-5%)를 설정하세요."
            )

        # 6. 물타기/매몰비용 감지
        sunk_cost_score = self._detect_pattern(message_lower, self.SUNK_COST_PATTERNS)
        if sunk_cost_score > 0:
            detected.append("sunk_cost")
            emotion_details["sunk_cost"] = sunk_cost_score
            total_score += sunk_cost_score * 0.20

            warnings.append(
                "⚠️ 물타기 주의: 손실 중인 포지션에 추가 자금을 투입하면 "
                "리스크가 배가됩니다. 손절 후 새로운 기회를 찾는 것이 낫습니다."
            )

        # 종합 점수 (0~1 범위)
        emotion_score = min(1.0, total_score)

        # 이성적 판단 여부
        is_rational = emotion_score < 0.25

        # 차단 여부 (0.6 이상이면 차단)
        should_block = emotion_score >= 0.6

        # 대안 조언 생성
        alternative = self._generate_alternative_advice(detected, emotion_score, recent_market_move)

        return EmotionAnalysis(
            detected_emotions=detected,
            emotion_score=round(emotion_score, 2),
            is_rational=is_rational,
            warnings=warnings,
            should_block=should_block,
            alternative_advice=alternative,
            emotion_details=emotion_details,
        )

    def _detect_pattern(self, text: str, patterns: list) -> float:
        """패턴 매칭으로 감정 점수 계산"""
        matches = 0
        for pattern in patterns:
            if re.search(pattern, text):
                matches += 1

        # 3개 이상 매칭 시 최대 점수
        return min(1.0, matches / 3)

    def _generate_alternative_advice(
        self,
        emotions: list,
        score: float,
        recent_market: dict = None
    ) -> str:
        """감정에 따른 대안 조언"""

        if "fomo" in emotions:
            if recent_market and recent_market.get('change_24h', 0) > 10:
                return (
                    "💡 대안: 지금 진입하는 대신, RSI 50 이하로 조정 시 분할 매수를 "
                    "설정하세요. 급등 후 진입보다 평균 수익률이 2배 높습니다. "
                    "구체적으로 현재가 대비 -5%, -10% 지점에 지정가 매수를 걸어두세요."
                )
            return (
                "💡 대안: 지금 진입하는 대신, 다음 조정(-5~10%) 시 분할 매수를 설정하세요. "
                "급등 후 진입보다 평균 수익률이 2배 높습니다."
            )

        if "fear" in emotions:
            return (
                "💡 대안: 전량 매도 대신, 50%만 정리하고 나머지는 원래 손절가까지 유지하세요. "
                "급락 후 반등 시 기회를 보존할 수 있습니다. 또는 분할 청산하여 평균 매도가를 "
                "높이세요."
            )

        if "revenge" in emotions:
            return (
                "💡 대안: 오늘은 거래를 쉬고, 내일 새로운 마음으로 시장을 보세요. "
                "연속 손실 후 24시간 휴식은 승률을 15% 높입니다. 복수 매매의 승률은 "
                "통계적으로 35% 미만입니다."
            )

        if "overconfidence" in emotions:
            return (
                "💡 대안: 확신이 클수록 포지션은 작게. 평소 사이즈의 50%로 시작하고, "
                "수익이 나면 추가 진입하세요. '확실한' 거래에서 파산하는 경우가 많습니다. "
                "최대 리스크는 자본의 2%로 제한하세요."
            )

        if "greed" in emotions:
            return (
                "💡 대안: 현실적인 목표 수익률(월 3-5%)을 설정하세요. 10배, 100배를 "
                "노리다가 원금을 잃는 것보다 꾸준히 수익을 쌓는 것이 장기적으로 훨씬 낫습니다. "
                "복리의 힘을 믿으세요."
            )

        if "sunk_cost" in emotions:
            return (
                "💡 대안: 물타기 대신, 손절 후 새로운 기회를 찾으세요. 손실 중인 포지션에 "
                "추가 투자하면 리스크가 배가됩니다. 차라리 그 자금으로 더 좋은 셋업에 "
                "진입하는 것이 기대값이 높습니다."
            )

        # 복합 감정
        if score > 0.5:
            return (
                "💡 대안: 지금은 거래하기 적절하지 않은 심리 상태입니다. "
                "30분간 차트를 끄고 다른 활동을 하세요. 그 후 냉정하게 "
                "기대값과 손익비를 계산한 뒤 결정하세요."
            )

        return "💡 객관적인 데이터를 기반으로 기대값을 계산한 뒤 결정하세요."

    def get_emotion_report(
        self,
        analysis: EmotionAnalysis
    ) -> str:
        """감정 분석 리포트 생성"""

        if analysis.is_rational:
            return "✅ 이성적인 요청으로 판단됩니다. 분석을 진행합니다."

        report_lines = [
            "=" * 50,
            "⚠️ 감정적 거래 경고",
            "=" * 50,
            "",
        ]

        # 감지된 감정
        emotion_names = {
            "fomo": "FOMO (놓칠까봐 두려움)",
            "fear": "공포 (손실 두려움)",
            "revenge": "복수 매매",
            "overconfidence": "과잉 확신",
            "greed": "탐욕",
            "sunk_cost": "매몰 비용 (물타기)",
        }

        report_lines.append("📊 감지된 감정:")
        for emotion in analysis.detected_emotions:
            name = emotion_names.get(emotion, emotion)
            score = analysis.emotion_details.get(emotion, 0) * 100
            report_lines.append(f"   - {name}: {score:.0f}%")

        report_lines.append("")
        report_lines.append(f"📈 종합 감정 점수: {analysis.emotion_score * 100:.0f}/100")
        report_lines.append(f"{'❌ 거래 차단 권장' if analysis.should_block else '⚠️ 주의 필요'}")
        report_lines.append("")

        # 경고 메시지
        if analysis.warnings:
            report_lines.append("⚠️ 경고:")
            for warning in analysis.warnings:
                report_lines.append(f"   {warning}")
            report_lines.append("")

        # 대안
        report_lines.append("💡 권장 조치:")
        report_lines.append(f"   {analysis.alternative_advice}")
        report_lines.append("")
        report_lines.append("=" * 50)

        return "\n".join(report_lines)


# 감정 상태 추적기 (세션용)
class EmotionTracker:
    """세션 중 감정 상태 추적"""

    def __init__(self):
        self.history = []
        self.consecutive_blocks = 0

    def record(self, analysis: EmotionAnalysis):
        """분석 결과 기록"""
        self.history.append({
            "timestamp": datetime.now(),
            "emotions": analysis.detected_emotions,
            "score": analysis.emotion_score,
            "blocked": analysis.should_block,
        })

        if analysis.should_block:
            self.consecutive_blocks += 1
        else:
            self.consecutive_blocks = 0

    def should_force_break(self) -> bool:
        """강제 휴식이 필요한지 확인"""
        # 연속 3회 차단되면 강제 휴식 권고
        return self.consecutive_blocks >= 3

    def get_session_summary(self) -> dict:
        """세션 요약"""
        if not self.history:
            return {"total_requests": 0}

        total = len(self.history)
        blocked = sum(1 for h in self.history if h["blocked"])
        avg_score = sum(h["score"] for h in self.history) / total

        # 가장 빈번한 감정
        all_emotions = []
        for h in self.history:
            all_emotions.extend(h["emotions"])

        emotion_counts = {}
        for e in all_emotions:
            emotion_counts[e] = emotion_counts.get(e, 0) + 1

        return {
            "total_requests": total,
            "blocked_requests": blocked,
            "block_rate": blocked / total * 100,
            "avg_emotion_score": avg_score,
            "most_common_emotion": max(emotion_counts, key=emotion_counts.get) if emotion_counts else None,
            "emotion_distribution": emotion_counts,
        }


if __name__ == "__main__":
    # 테스트
    filter = EmotionFilter()

    test_cases = [
        # FOMO
        ("비트코인 급등하는데 지금 안 사면 늦겠어!", {"change_24h": 15}, None),
        # 공포
        ("망했다 폭락한다 다 팔아야겠어", {"change_24h": -12}, None),
        # 복수 매매
        ("아까 손절했는데 다시 들어가서 원금 회복해야해", None, {"pnl": -50000, "pnl_pct": -5}),
        # 과잉 확신
        ("이건 무조건 간다 올인해야지 레버리지 20배로", None, None),
        # 탐욕
        ("이번엔 100배 대박 가즈아!!!", None, None),
        # 물타기
        ("물렸는데 평단 낮추려고 물타기 해야겠어", None, None),
        # 정상
        ("BTC RSI가 35인데 지지선 근처에서 매수 검토해볼까?", None, None),
    ]

    print("=" * 60)
    print("감정 필터 테스트")
    print("=" * 60)

    for msg, market, trade in test_cases:
        print(f"\n입력: \"{msg}\"")
        analysis = filter.analyze_request(msg, market, trade)
        print(f"감지된 감정: {analysis.detected_emotions}")
        print(f"감정 점수: {analysis.emotion_score:.2f}")
        print(f"이성적: {analysis.is_rational}")
        print(f"차단: {analysis.should_block}")
        if analysis.warnings:
            print(f"경고: {analysis.warnings[0][:50]}...")
        print(f"대안: {analysis.alternative_advice[:50]}...")
        print("-" * 40)
