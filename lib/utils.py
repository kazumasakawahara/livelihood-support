"""
生活保護受給者尊厳支援データベース - ユーティリティモジュール
共通ヘルパー関数、和暦変換、セッション管理
"""

import re
import streamlit as st
from datetime import datetime, date


# =============================================================================
# 元号（和暦）定義
# =============================================================================

GENGO_MAP = {
    '明治': {'start': 1868, 'end': 1912},
    '大正': {'start': 1912, 'end': 1926},
    '昭和': {'start': 1926, 'end': 1989},
    '平成': {'start': 1989, 'end': 2019},
    '令和': {'start': 2019, 'end': 9999},
    'M': {'start': 1868, 'end': 1912},
    'T': {'start': 1912, 'end': 1926},
    'S': {'start': 1926, 'end': 1989},
    'H': {'start': 1989, 'end': 2019},
    'R': {'start': 2019, 'end': 9999},
}


def convert_wareki_to_seireki(wareki_str: str) -> str | None:
    """
    和暦（元号）を西暦（YYYY-MM-DD形式）に変換
    """
    if not wareki_str:
        return None

    wareki_str = str(wareki_str).strip()

    # パターン1: 「昭和50年3月15日」形式
    pattern1 = r'^(明治|大正|昭和|平成|令和)(\d{1,2})年(\d{1,2})月(\d{1,2})日?$'
    match = re.match(pattern1, wareki_str)
    if match:
        gengo, year, month, day = match.groups()
        return _convert_gengo_to_date(gengo, int(year), int(month), int(day))

    # パターン2: 「S50.3.15」形式
    pattern2 = r'^([MTSHR])(\d{1,2})[./\-](\d{1,2})[./\-](\d{1,2})$'
    match = re.match(pattern2, wareki_str.upper())
    if match:
        gengo, year, month, day = match.groups()
        return _convert_gengo_to_date(gengo, int(year), int(month), int(day))

    # パターン3: 「昭和50/3/15」形式
    pattern3 = r'^(明治|大正|昭和|平成|令和)(\d{1,2})[./\-](\d{1,2})[./\-](\d{1,2})$'
    match = re.match(pattern3, wareki_str)
    if match:
        gengo, year, month, day = match.groups()
        return _convert_gengo_to_date(gengo, int(year), int(month), int(day))

    return None


def _convert_gengo_to_date(gengo: str, year: int, month: int, day: int) -> str | None:
    """元号・年・月・日から西暦日付文字列を生成"""
    if gengo not in GENGO_MAP:
        return None

    gengo_info = GENGO_MAP[gengo]
    seireki_year = gengo_info['start'] + year - 1

    try:
        result_date = date(seireki_year, month, day)
        return result_date.strftime("%Y-%m-%d")
    except ValueError:
        return None


def safe_date_parse(date_str: str) -> date | None:
    """
    日付文字列を安全にパース（元号対応）
    """
    if not date_str:
        return None

    date_str = str(date_str).strip()

    # 1. 西暦YYYY-MM-DD形式
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        pass

    # 2. 西暦YYYY/MM/DD形式
    try:
        return datetime.strptime(date_str, "%Y/%m/%d").date()
    except (ValueError, TypeError):
        pass

    # 3. 和暦形式を西暦に変換して再パース
    seireki = convert_wareki_to_seireki(date_str)
    if seireki:
        try:
            return datetime.strptime(seireki, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass

    return None


def calculate_age(birth_date: date | str, reference_date: date = None) -> int | None:
    """生年月日から年齢を計算"""
    if birth_date is None:
        return None

    if isinstance(birth_date, str):
        birth_date = safe_date_parse(birth_date)
        if birth_date is None:
            return None

    if reference_date is None:
        reference_date = date.today()

    age = reference_date.year - birth_date.year
    if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
        age -= 1

    return age if age >= 0 else None


def format_date_with_age(birth_date: date | str) -> str:
    """生年月日と年齢を整形して返す"""
    if birth_date is None:
        return "不明"

    if isinstance(birth_date, str):
        parsed = safe_date_parse(birth_date)
        if parsed is None:
            return birth_date
        birth_date = parsed

    age = calculate_age(birth_date)
    date_str = birth_date.strftime("%Y-%m-%d")

    if age is not None:
        return f"{date_str}（{age}歳）"
    return date_str


# =============================================================================
# Streamlit セッション管理
# =============================================================================

def init_session_state():
    """Streamlitセッション状態の初期化"""
    if 'step' not in st.session_state:
        st.session_state.step = 'input'
    if 'extracted_data' not in st.session_state:
        st.session_state.extracted_data = None
    if 'edited_data' not in st.session_state:
        st.session_state.edited_data = None
    if 'narrative_text' not in st.session_state:
        st.session_state.narrative_text = ""
    if 'uploaded_file_text' not in st.session_state:
        st.session_state.uploaded_file_text = ""
    if 'caseworker_name' not in st.session_state:
        st.session_state.caseworker_name = ""


def reset_session_state():
    """セッション状態をリセット"""
    st.session_state.step = 'input'
    st.session_state.extracted_data = None
    st.session_state.edited_data = None
    st.session_state.narrative_text = ""
    st.session_state.uploaded_file_text = ""


def get_input_example() -> str:
    """入力例テキストを取得（ケース記録の例）"""
    return """12/27訪問（15分）。チャイムを鳴らすと3分ほどで応答。
部屋は散らかっていたが、前回より改善。
「最近は朝起きられるようになった」とのこと。

就労の話を振ると視線を落とし黙り込んだため、話題を変えた。
「今は働くことより、毎日起きられるようになったことが嬉しい」と話していた。

短時間で切り上げたことで、最後は笑顔で「また来てください」と言ってくれた。

【本人情報】
山田太郎さん（45歳・男性）
うつ病で通院中（北九州市立医療センター・佐藤医師）
令和5年10月から保護開始

【本人の話】
「前の会社でパワハラを受けて、それから調子が悪くなった」
「できれば、もう一度働きたいとは思っている」

【家族状況】
元妻との間に娘がいるが、5年前に離婚してから会っていない。
実母は健在だが、関係は疎遠。

【連絡先】
緊急時は民生委員の田中さん（090-xxxx-xxxx）に連絡

次回訪問は2週間後。就労の話題は避け、生活リズムの確認を中心に。
記録者：鈴木ケースワーカー"""


# =============================================================================
# 表示用ヘルパー
# =============================================================================

def get_risk_emoji(risk_level: str) -> str:
    """リスクレベルに応じた絵文字を返す"""
    return {"High": "🔴", "Medium": "🟠", "Low": "🟡"}.get(risk_level, "⚪")


def get_status_badge(status: str) -> str:
    """ステータスに応じたバッジHTMLを返す"""
    colors = {
        "Active": "#28a745",
        "Improving": "#17a2b8",
        "Resolved": "#6c757d",
        "High": "#dc3545",
        "Medium": "#fd7e14",
        "Low": "#ffc107"
    }
    color = colors.get(status, "#6c757d")
    return f'<span style="background-color: {color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em;">{status}</span>'


def format_mental_health_warning(diagnosis: str) -> str:
    """精神疾患の警告メッセージを生成"""
    return f"""⚠️ この方は精神疾患（{diagnosis}）を抱えています。
以下の対応は症状を悪化させる可能性があります：
- 批判的な言葉かけ（「なぜ○○しないのか」等）
- 就労への性急な圧力
- 約束や期限の強要
- 長時間の面談

本人のペースを尊重し、伴走する姿勢で関わってください。"""
