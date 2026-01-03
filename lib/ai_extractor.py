"""
生活保護受給者尊厳支援データベース - AI構造化モジュール
Manifesto: Livelihood Protection Support & Dignity Graph 準拠（Version 1.4）

ケース記録・物語風テキストからの情報抽出、JSON構造化処理
第7の柱（金銭的安全と多機関連携）対応

セキュリティ基準:
- TECHNICAL_STANDARDS.md 7.2準拠（プロンプトインジェクション対策）
- TECHNICAL_STANDARDS.md 8準拠（外部AI利用時の匿名化）
"""

import os
import re
import json
import sys
from datetime import date
from typing import Optional
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google import Gemini

from lib.anonymizer import (
    Anonymizer,
    AnonymizationResult,
    create_anonymizer,
)

load_dotenv()


# =============================================================================
# 入力値検証・セキュリティ（TECHNICAL_STANDARDS.md 7.2準拠）
# =============================================================================

class InputValidationError(Exception):
    """入力値検証エラー"""
    pass


# プロンプトインジェクション検出パターン
PROMPT_INJECTION_PATTERNS = [
    r'ignore\s+(previous|above|all)\s+instructions?',
    r'disregard\s+(above|previous|the)',
    r'new\s+instructions?\s*:',
    r'システムプロンプト',
    r'system\s*prompt',
    r'forget\s+(everything|all)',
    r'override\s+(instructions?|rules?)',
    r'you\s+are\s+now',
    r'pretend\s+to\s+be',
    r'act\s+as\s+if',
    r'ignore\s+your\s+training',
    r'bypass\s+(safety|security)',
    r'jailbreak',
]


def detect_prompt_injection(text: str) -> list[str]:
    """
    プロンプトインジェクションの検出

    Args:
        text: 検査対象のテキスト

    Returns:
        検出されたパターンのリスト（空の場合は安全）
    """
    if not text:
        return []

    detected = []
    text_lower = text.lower()

    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            detected.append(pattern)

    return detected


def sanitize_for_prompt(text: str, max_length: int = 50000) -> str:
    """
    プロンプト用の入力サニタイズ（TECHNICAL_STANDARDS.md 7.2準拠）

    Args:
        text: サニタイズ対象のテキスト
        max_length: 最大文字数

    Returns:
        サニタイズ済みテキスト

    Raises:
        InputValidationError: 不正な入力を検出した場合
    """
    if not text:
        raise InputValidationError("入力テキストが空です")

    # 長さチェック
    if len(text) > max_length:
        raise InputValidationError(f"入力テキストは{max_length}文字以内にしてください")

    # プロンプトインジェクション検出
    injections = detect_prompt_injection(text)
    if injections:
        log(f"⚠️ プロンプトインジェクション検出: {injections}", "WARN")
        raise InputValidationError("不正な入力パターンが検出されました。入力内容を確認してください。")

    # 制御文字の除去（改行・タブは保持）
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    return cleaned


def validate_input_text(text: str, recipient_name: str = None) -> tuple[str, str | None]:
    """
    入力テキストの総合検証

    Args:
        text: 入力テキスト
        recipient_name: 受給者名（オプション）

    Returns:
        (検証済みテキスト, 検証済み受給者名)

    Raises:
        InputValidationError: 検証失敗時
    """
    # テキストのサニタイズ
    validated_text = sanitize_for_prompt(text)

    # 受給者名の検証（指定されている場合）
    validated_name = None
    if recipient_name:
        if len(recipient_name) > 100:
            raise InputValidationError("受給者名は100文字以内にしてください")
        # 受給者名にもインジェクションチェック
        if detect_prompt_injection(recipient_name):
            raise InputValidationError("受給者名に不正なパターンが含まれています")
        validated_name = recipient_name.strip()

    return validated_text, validated_name


# --- ログ出力 ---
def log(message: str, level: str = "INFO"):
    """ログ出力（標準エラー出力）"""
    sys.stderr.write(f"[AI_Extractor:{level}] {message}\n")
    sys.stderr.flush()


# =============================================================================
# AI抽出用プロンプト（マニフェスト Version 1.4 準拠）
# =============================================================================

EXTRACTION_PROMPT = """
あなたは「生活保護受給者尊厳支援データベース」のデータ抽出専門家です。
ケースワーカーが作成したケース記録・家庭訪問記録・面談メモなどから、
支援に必要な情報を**JSON形式で**抽出してください。

【最重要：二次被害防止と経済的安全の観点】
このデータベースの目的は、受給者を「ケース番号」ではなく「尊厳ある個人」として
支援することです。特に以下の点に注意して抽出してください：

1. **強み（Strength）の発見を優先**: 課題だけでなく、本人の良い面・できることを必ず抽出
2. **効果的だった関わり方**: 「〜したら落ち着いた」「〜で笑顔になった」を必ず拾う
3. **避けるべき関わり方（NgApproach）**: 「〜したら黙り込んだ」「〜で表情が曇った」を漏らさない
4. **経済的リスクの発見**: 「お金がない」「〇〇に渡した」「家族に取られた」などを必ず拾う
5. **金銭管理の困難さ**: 「受給日から数日で使い果たす」などのパターンを抽出
6. **多機関連携**: 社協、地域包括、医療機関との連携内容を記録
7. **批判的表現の変換**: 「怠惰」→「活動が制限されている」など、疾患を考慮した表現に

【日付の変換ルール】
元号（和暦）で入力された日付は必ず西暦（YYYY-MM-DD形式）に変換してください：
- 昭和元年=1926年、平成元年=1989年、令和元年=2019年
- 「今日」「本日」は {today} として処理
- 「昨日」は日付から1日引いた日付
- 「先週」「先月」は適切に推定

【出力形式】
必ず以下のJSON構造で出力してください。該当がない項目は空配列[]としてください。

```json
{{
  "recipient": {{
    "caseNumber": "ケース番号（あれば）",
    "name": "氏名（必須）",
    "dob": "生年月日（YYYY-MM-DD形式、不明なら null）",
    "gender": "性別（男性/女性/その他/不明）",
    "address": "住所",
    "protectionStartDate": "保護開始日（YYYY-MM-DD形式）"
  }},
  
  "caseRecords": [
    {{
      "date": "記録日（YYYY-MM-DD形式）",
      "category": "相談/訪問/電話/来所/同行/会議/その他",
      "content": "記録内容（原文をできるだけ忠実に）",
      "caseworker": "記録者名",
      "recipientResponse": "本人の反応・様子",
      "observations": ["観察された事実1", "観察された事実2"]
    }}
  ],
  
  "strengths": [
    {{
      "description": "強み・できること",
      "discoveredDate": "発見日（YYYY-MM-DD形式）",
      "context": "どんな場面で発揮されたか",
      "sourceRecord": "根拠となる記録の要約"
    }}
  ],
  
  "challenges": [
    {{
      "description": "課題・困難",
      "severity": "High/Medium/Low",
      "currentStatus": "Active/Improving/Resolved",
      "supportNeeded": "必要な支援"
    }}
  ],
  
  "mentalHealthStatus": {{
    "diagnosis": "診断名（うつ病、統合失調症など）",
    "currentStatus": "安定/不安定/改善傾向/悪化傾向",
    "symptoms": ["症状1", "症状2"],
    "treatmentStatus": "通院中/入院中/治療中断/未受診",
    "lastAssessment": "最終確認日（YYYY-MM-DD形式）"
  }},
  
  "effectiveApproaches": [
    {{
      "description": "効果があった関わり方",
      "context": "どんな状況で効果的だったか",
      "frequency": "繰り返し効果あり/初回のみ/状況依存"
    }}
  ],
  
  "ngApproaches": [
    {{
      "description": "避けるべき関わり方",
      "reason": "なぜ避けるべきか",
      "riskLevel": "High/Medium/Low",
      "consequence": "実際に起きた結果（あれば）"
    }}
  ],
  
  "triggerSituations": [
    {{
      "description": "注意が必要な状況",
      "signs": ["サイン1", "サイン2"],
      "recommendedResponse": "推奨される対応"
    }}
  ],
  
  "moneyManagementStatus": {{
    "capability": "自己管理可能/支援があれば可能/支援が必要/困難/不明",
    "pattern": "金銭管理のパターン（例：受給日から数日で使い果たす）",
    "riskLevel": "High/Medium/Low",
    "triggers": ["きっかけ1", "きっかけ2"],
    "observations": "観察された状況",
    "assessmentDate": "評価日（YYYY-MM-DD形式）"
  }},
  
  "economicRisks": [
    {{
      "type": "金銭搾取/無心・たかり/通帳管理強要/借金の肩代わり強要/年金・手当の横領/住居費の搾取/詐欺被害リスク/浪費",
      "perpetrator": "加害者名（わかれば）",
      "perpetratorRelationship": "続柄（長男、母、元配偶者など）",
      "severity": "High/Medium/Low",
      "description": "状況の詳細",
      "discoveredDate": "発見日（YYYY-MM-DD形式）",
      "status": "Active/Monitoring/Resolved",
      "interventions": ["実施した介入1", "介入2"]
    }}
  ],
  
  "dailyLifeSupportService": {{
    "socialWelfareCouncil": "社会福祉協議会名",
    "startDate": "利用開始日（YYYY-MM-DD形式）",
    "services": ["福祉サービス利用援助", "日常的金銭管理サービス", "書類等預かりサービス"],
    "frequency": "利用頻度",
    "specialist": "担当者名",
    "contactInfo": "連絡先",
    "status": "利用中/利用終了/検討中",
    "referralRoute": "地域包括支援センター経由/福祉事務所から直接/医療機関から紹介/その他",
    "reason": "利用理由"
  }},
  
  "collaborationRecords": [
    {{
      "date": "日付（YYYY-MM-DD形式）",
      "type": "ケース会議/情報共有/緊急対応/定期連絡",
      "participants": ["参加者1（所属）", "参加者2（所属）"],
      "agenda": "議題",
      "discussion": "協議内容",
      "decisions": ["決定事項1", "決定事項2"],
      "nextActions": ["次回アクション1", "アクション2"],
      "involvedOrganizations": ["関係機関名1", "機関名2"]
    }}
  ],
  
  "declaredHistories": [
    {{
      "era": "時期（幼少期/学齢期/20代/30代など）",
      "content": "本人が語った内容",
      "reliability": "Declared（本人申告）",
      "declaredDate": "聴取日（YYYY-MM-DD形式）"
    }}
  ],
  
  "pathwayToProtection": {{
    "declaredTrigger": "本人が語った保護に至ったきっかけ",
    "declaredTimeline": "時系列の概要",
    "reliability": "Declared（本人申告）"
  }},
  
  "wishes": [
    {{
      "content": "本人の願い・希望",
      "priority": "High/Medium/Low",
      "declaredDate": "記録日（YYYY-MM-DD形式）",
      "status": "Active/Achieved/Archived"
    }}
  ],
  
  "keyPersons": [
    {{
      "name": "氏名",
      "relationship": "関係（友人、元同僚、民生委員など）",
      "contactInfo": "連絡先",
      "rank": 1,
      "role": "役割（緊急連絡先、相談相手など）",
      "lastContact": "最終連絡日"
    }}
  ],
  
  "familyMembers": [
    {{
      "name": "氏名",
      "relationship": "続柄（母、兄、元配偶者など）",
      "contactStatus": "良好/疎遠/断絶/不明",
      "supportCapacity": "支援可能/困難/不明",
      "note": "備考",
      "riskFlag": "経済的リスクがある場合 true"
    }}
  ],
  
  "supportOrganizations": [
    {{
      "name": "機関名",
      "type": "社会福祉協議会/地域包括支援センター/NPO/就労支援/精神保健/その他",
      "contactPerson": "担当者名",
      "phone": "電話番号",
      "services": "提供サービス",
      "utilizationStatus": "利用中/利用終了/紹介済/未利用"
    }}
  ],
  
  "medicalInstitutions": [
    {{
      "name": "医療機関名",
      "department": "診療科",
      "doctor": "担当医名",
      "role": "主治医/専門医/かかりつけ",
      "visitFrequency": "通院頻度"
    }}
  ],
  
  "protectionDecision": {{
    "decisionDate": "決定日（YYYY-MM-DD形式）",
    "type": "開始/変更/廃止",
    "protectionCategory": "世帯区分",
    "monthlyAmount": "月額（数値）"
  }},
  
  "certificates": [
    {{
      "type": "障害者手帳/介護保険証/自立支援医療/その他",
      "grade": "等級",
      "expiryDate": "有効期限（YYYY-MM-DD形式）"
    }}
  ],
  
  "supportGoals": [
    {{
      "description": "支援目標",
      "targetDate": "目標達成予定日",
      "status": "Active/Achieved/Modified/Abandoned",
      "paceConsideration": "本人のペースに関する配慮事項"
    }}
  ],
  
  "patterns": [
    {{
      "description": "発見されたパターン",
      "frequency": "頻度",
      "triggers": ["きっかけ1", "きっかけ2"]
    }}
  ]
}}
```

【抽出ルール - 優先順位順】

1. **避けるべき関わり方（ngApproaches）** - 最重要！二次被害防止
   - 「指導した」「注意した」→ 本人の反応を確認し、ネガティブなら登録
   - 「就労を促した」（精神疾患あり）→ 要注意として登録
   - 「約束させた」「期限を設けた」→ プレッシャーリスクとして登録
   - 「黙り込んだ」「表情が曇った」「視線を落とした」→ この対応を避けるべきとして登録

2. **経済的リスク（economicRisks）** - 最重要！経済的安全
   - 「お金がない」「足りない」→ 原因を探る
   - 「〇〇に渡した」「持っていかれた」→ 金銭搾取として登録
   - 「息子が来てお金を」「家族にせびられる」→ 親族による搾取として登録
   - 「受給日から数日で」→ 金銭管理困難として登録
   - 「通帳を預けている」「カードを持っている」→ 管理強要リスクとして確認

3. **金銭管理状況（moneyManagementStatus）**
   - 「計画的に使えない」「すぐに使ってしまう」
   - 「公共料金の滞納」「食料がない」

4. **日常生活自立支援事業（dailyLifeSupportService）**
   - 「社協」「日自」「金銭管理サービス」への言及
   - 利用状況、担当者、サービス内容

5. **多機関連携（collaborationRecords）**
   - 「ケース会議」「カンファレンス」「情報共有」
   - 参加者、議題、決定事項、次回アクション

6. **効果的だった関わり方（effectiveApproaches）**
   - 「〜したら落ち着いた」「〜で笑顔になった」
   - 「短時間で切り上げた」「話題を変えた」など

7. **強み（strengths）** - 課題より先に抽出
   - 「〜ができる」「〜が得意」「〜を続けている」
   - 「自発的に〜した」「意欲を見せた」

8. **ケース記録（caseRecords）**
   - 日付、記録者、内容、本人の反応を忠実に抽出

9. **精神疾患の状況（mentalHealthStatus）**
   - 診断名、症状、治療状況を正確に

10. **その他の情報**
    - 申告歴、ネットワーク、法的基盤など

【経済的リスク検出のヒント】
以下の表現は経済的リスクのサインとして注意深く抽出してください：

| 表現例 | リスク種別 |
|--------|----------|
| 「お金がない」「足りない」（受給日直後） | 金銭搾取または浪費 |
| 「息子（娘・兄弟）が来てお金を」 | 親族による金銭搾取 |
| 「家族に渡した」「持っていかれた」 | 金銭搾取 |
| 「断ると怒られる」「怒鳴られる」 | 無心・たかり |
| 「通帳を預けている」 | 通帳管理強要（要確認） |
| 「借金を返すために」「代わりに払った」 | 借金の肩代わり強要 |
| 「家賃を多く払っている」 | 住居費の搾取 |
| 「電話で〇〇に送金した」 | 詐欺被害リスク |
| 「パチンコ」「競馬」「ギャンブル」 | 浪費（本人） |

【批判的表現の変換ガイド】
入力テキストに以下のような表現があった場合、適切に変換してください：

| 入力表現 | 変換後 |
|---------|--------|
| 「怠惰」「怠けている」 | 「症状により活動が制限されている」 |
| 「指導した」 | （本人反応を確認し）「情報提供した」 |
| 「改善しない」 | 「現時点では変化が見られない」 |
| 「嘘をついている」 | 「申告内容と記録に相違がある」 |
| 「問題ケース」 | 「複合的な支援ニーズがある」 |
| 「金遣いが荒い」 | 「金銭管理に支援が必要」 |
| 「家族に甘い」 | 「家族との関係性に課題がある」 |

【禁止事項】
- JSON以外のテキストを出力しない
- ```json と ``` で囲んで出力する
- テキストにない情報を創作しない
- 批判的な表現をそのまま出力しない
"""

# --- AIエージェント ---
_agent = None


def get_agent():
    """AIエージェントを取得（シングルトン）"""
    global _agent
    if _agent is None:
        _agent = Agent(
            model=Gemini(id="gemini-2.0-flash-exp", api_key=os.getenv("GEMINI_API_KEY")),
            description="ケース記録から構造化データを抽出する専門家（二次被害防止・経済的安全重視）",
            instructions=[EXTRACTION_PROMPT.format(today=date.today().isoformat())],
            markdown=True
        )
    return _agent


def parse_json_from_response(response_text: str) -> dict | None:
    """
    AIレスポンスからJSONを抽出
    
    Args:
        response_text: AIからのレスポンステキスト
        
    Returns:
        パースされたdict、または失敗時はNone
    """
    try:
        # ```json ... ``` を抽出
        pattern = r'```json\s*(.*?)\s*```'
        match = re.search(pattern, response_text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        # そのままJSONとしてパース試行
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        log(f"JSONパースエラー: {e}", "WARN")
        return None


def extract_from_text(text: str, recipient_name: str = None) -> dict | None:
    """
    テキストから構造化データを抽出

    Args:
        text: 入力テキスト（ケース記録、面談メモなど）
        recipient_name: 既存受給者名（追記モードの場合）

    Returns:
        構造化されたdict、または失敗時はNone

    Raises:
        InputValidationError: 入力検証に失敗した場合
    """
    # 入力値検証（TECHNICAL_STANDARDS.md 7.2準拠）
    try:
        validated_text, validated_name = validate_input_text(text, recipient_name)
    except InputValidationError as e:
        log(f"入力検証エラー: {e}", "ERROR")
        raise

    agent = get_agent()

    # 追記モードの場合、受給者名を追加
    prompt_text = validated_text
    if validated_name:
        prompt_text = f"【対象受給者: {validated_name}】\n\n{validated_text}"

    try:
        log(f"テキスト抽出開始（{len(validated_text)}文字）")
        response = agent.run(
            f"以下のケース記録・報告書から情報を抽出してJSON形式で出力してください：\n\n{prompt_text}"
        )

        extracted = parse_json_from_response(response.content)

        if extracted:
            # 追記モードの場合、受給者名を設定
            if validated_name and extracted.get('recipient'):
                extracted['recipient']['name'] = validated_name
            
            name = extracted.get('recipient', {}).get('name', '不明')
            log(f"抽出成功: 受給者={name}")
            
            # 抽出サマリーをログ出力
            _log_extraction_summary(extracted)
            
            return extracted

        log("JSONパース失敗: AIレスポンスからJSONを抽出できませんでした", "WARN")
        return None

    except Exception as e:
        log(f"抽出エラー: {type(e).__name__}: {e}", "ERROR")
        return None


def _log_extraction_summary(data: dict):
    """抽出結果のサマリーをログ出力"""
    summary_items = []
    
    if data.get('caseRecords'):
        summary_items.append(f"ケース記録: {len(data['caseRecords'])}件")
    if data.get('strengths'):
        summary_items.append(f"強み: {len(data['strengths'])}件")
    if data.get('ngApproaches'):
        summary_items.append(f"⚠️避けるべき関わり方: {len(data['ngApproaches'])}件")
    if data.get('effectiveApproaches'):
        summary_items.append(f"効果的な関わり方: {len(data['effectiveApproaches'])}件")
    if data.get('mentalHealthStatus', {}).get('diagnosis'):
        summary_items.append(f"精神疾患: {data['mentalHealthStatus']['diagnosis']}")
    
    # 第7の柱関連
    if data.get('economicRisks'):
        summary_items.append(f"⚠️経済的リスク: {len(data['economicRisks'])}件")
    if data.get('moneyManagementStatus', {}).get('capability'):
        summary_items.append(f"金銭管理: {data['moneyManagementStatus']['capability']}")
    if data.get('dailyLifeSupportService', {}).get('socialWelfareCouncil'):
        summary_items.append(f"日自支援: {data['dailyLifeSupportService']['status']}")
    if data.get('collaborationRecords'):
        summary_items.append(f"連携記録: {len(data['collaborationRecords'])}件")
    
    if summary_items:
        log(f"抽出サマリー: {', '.join(summary_items)}")


def validate_extracted_data(data: dict) -> tuple[bool, list[str]]:
    """
    抽出データの検証
    
    Args:
        data: 抽出されたデータ
        
    Returns:
        (検証成功フラグ, エラーメッセージのリスト)
    """
    errors = []
    warnings = []
    
    # 必須項目チェック
    if not data.get('recipient', {}).get('name'):
        errors.append("受給者名は必須です")
    
    # 精神疾患がある場合の警告チェック
    mental_health = data.get('mentalHealthStatus', {})
    if mental_health.get('diagnosis'):
        # NgApproachが空の場合は警告
        if not data.get('ngApproaches'):
            warnings.append("⚠️ 精神疾患がありますが、避けるべき関わり方が抽出されていません。記録を確認してください。")
    
    # 経済的リスクがある場合の警告チェック
    economic_risks = data.get('economicRisks', [])
    high_severity_risks = [r for r in economic_risks if r.get('severity') == 'High']
    if high_severity_risks:
        # 日常生活自立支援事業の検討を促す
        if not data.get('dailyLifeSupportService', {}).get('socialWelfareCouncil'):
            warnings.append("⚠️ 深刻な経済的リスクがありますが、日常生活自立支援事業の利用がありません。導入を検討してください。")
    
    # 金銭管理困難の場合のチェック
    money_status = data.get('moneyManagementStatus', {})
    if money_status.get('capability') in ['困難', '支援が必要']:
        if not data.get('dailyLifeSupportService', {}).get('socialWelfareCouncil'):
            warnings.append("⚠️ 金銭管理に支援が必要ですが、日常生活自立支援事業の利用がありません。導入を検討してください。")
    
    # エラーがなければ成功（警告は許容）
    return len(errors) == 0, errors + warnings


def detect_critical_expressions(text: str) -> list[dict]:
    """
    批判的な表現を検出
    
    Args:
        text: 入力テキスト
        
    Returns:
        検出された表現と推奨変換のリスト
    """
    critical_patterns = [
        {"pattern": r"怠[惰け]", "original": "怠惰/怠けている", "suggested": "症状により活動が制限されている"},
        {"pattern": r"指導した", "original": "指導した", "suggested": "情報提供した（本人の反応を確認）"},
        {"pattern": r"改善しない", "original": "改善しない", "suggested": "現時点では変化が見られない"},
        {"pattern": r"嘘", "original": "嘘をついている", "suggested": "申告内容と記録に相違がある"},
        {"pattern": r"問題ケース", "original": "問題ケース", "suggested": "複合的な支援ニーズがある"},
        {"pattern": r"言うことを聞かない", "original": "言うことを聞かない", "suggested": "本人の意向と支援方針に相違がある"},
        {"pattern": r"何度言っても", "original": "何度言っても", "suggested": "別のアプローチを検討する必要がある"},
        {"pattern": r"金遣いが荒い", "original": "金遣いが荒い", "suggested": "金銭管理に支援が必要"},
        {"pattern": r"家族に甘い", "original": "家族に甘い", "suggested": "家族との関係性に課題がある"},
    ]
    
    detected = []
    for p in critical_patterns:
        if re.search(p["pattern"], text):
            detected.append({
                "original": p["original"],
                "suggested": p["suggested"]
            })
    
    return detected


def detect_economic_risk_signals(text: str) -> list[dict]:
    """
    経済的リスクのサインを検出
    
    Args:
        text: 入力テキスト
        
    Returns:
        検出されたリスクサインのリスト
    """
    risk_patterns = [
        {
            "pattern": r"(お金が|金が)(ない|足りない|なくなった)",
            "signal": "金銭不足",
            "possible_causes": ["金銭搾取", "浪費", "金銭管理困難"]
        },
        {
            "pattern": r"(息子|娘|兄|弟|姉|妹|親|母|父|家族|親戚).*(渡した|持っていかれた|取られた|せびられた)",
            "signal": "親族への金銭流出",
            "possible_causes": ["金銭搾取"]
        },
        {
            "pattern": r"(息子|娘|兄|弟|姉|妹|親|母|父|家族|親戚).*(来て|来ると).*(お金|金)",
            "signal": "親族の訪問と金銭の関連",
            "possible_causes": ["金銭搾取", "無心・たかり"]
        },
        {
            "pattern": r"(断ると|断れない|断れなくて).*(怒|怖)",
            "signal": "金銭要求への恐怖",
            "possible_causes": ["無心・たかり", "金銭搾取"]
        },
        {
            "pattern": r"通帳.*(預けている|渡している|管理されている)",
            "signal": "通帳の他者管理",
            "possible_causes": ["通帳管理強要"]
        },
        {
            "pattern": r"受給日.*(数日|すぐ|直後).*(ない|なくなる|使い果たす)",
            "signal": "受給日直後の金銭枯渇",
            "possible_causes": ["金銭搾取", "浪費", "金銭管理困難"]
        },
        {
            "pattern": r"(パチンコ|競馬|競輪|ギャンブル|賭|スロット)",
            "signal": "ギャンブルへの言及",
            "possible_causes": ["浪費"]
        },
        {
            "pattern": r"(借金|ローン|返済).*(代わりに|肩代わり)",
            "signal": "借金の肩代わり",
            "possible_causes": ["借金の肩代わり強要"]
        },
        {
            "pattern": r"(電話|メール|SMS).*(送金|振込|払った)",
            "signal": "遠隔での送金",
            "possible_causes": ["詐欺被害リスク"]
        },
    ]
    
    detected = []
    for p in risk_patterns:
        if re.search(p["pattern"], text):
            detected.append({
                "signal": p["signal"],
                "possible_causes": p["possible_causes"]
            })
    
    if detected:
        log(f"⚠️ 経済的リスクサイン検出: {len(detected)}件", "WARN")
    
    return detected


def detect_collaboration_signals(text: str) -> list[dict]:
    """
    多機関連携のサインを検出
    
    Args:
        text: 入力テキスト
        
    Returns:
        検出された連携サインのリスト
    """
    collab_patterns = [
        {
            "pattern": r"(ケース会議|カンファレンス|支援会議)",
            "type": "ケース会議"
        },
        {
            "pattern": r"(社協|社会福祉協議会)",
            "type": "社会福祉協議会との連携"
        },
        {
            "pattern": r"(地域包括|包括支援)",
            "type": "地域包括支援センターとの連携"
        },
        {
            "pattern": r"(日常生活自立支援|日自|金銭管理サービス)",
            "type": "日常生活自立支援事業"
        },
        {
            "pattern": r"(主治医|病院|クリニック).*(連絡|相談|報告)",
            "type": "医療機関との連携"
        },
    ]
    
    detected = []
    for p in collab_patterns:
        if re.search(p["pattern"], text):
            detected.append({"type": p["type"]})

    return detected


# =============================================================================
# 匿名化統合機能（TECHNICAL_STANDARDS.md Section 8準拠）
# =============================================================================

# グローバル匿名化エンジンインスタンス
_anonymizer: Optional[Anonymizer] = None


def get_anonymizer() -> Anonymizer:
    """匿名化エンジンを取得（シングルトン）"""
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = create_anonymizer()
    return _anonymizer


def extract_from_text_with_anonymization(
    text: str,
    recipient_name: str = None,
    use_anonymization: bool = True
) -> tuple[dict | None, AnonymizationResult | None]:
    """
    外部AI利用時の匿名化対応版テキスト抽出

    TECHNICAL_STANDARDS.md Section 8.2 準拠
    外部AIサービスにデータを送信する前に自動的にPIIを匿名化し、
    結果を受信後に再識別（復元）します。

    Args:
        text: 入力テキスト（ケース記録、面談メモなど）
        recipient_name: 既存受給者名（追記モードの場合）
        use_anonymization: 匿名化を使用するかどうか（デフォルト: True）

    Returns:
        (構造化されたdict, 匿名化結果) のタプル
        - 失敗時は (None, None)
        - use_anonymization=False の場合は (dict, None)

    Raises:
        InputValidationError: 入力検証に失敗した場合

    Usage:
        # 外部AI利用時（匿名化あり）
        extracted, anon_result = extract_from_text_with_anonymization(text)
        if extracted:
            # 抽出されたデータは復元済み
            print(f"受給者: {extracted['recipient']['name']}")

        # ローカルLLM利用時（匿名化なし）
        extracted, _ = extract_from_text_with_anonymization(text, use_anonymization=False)
    """
    # 入力値検証（TECHNICAL_STANDARDS.md 7.2準拠）
    try:
        validated_text, validated_name = validate_input_text(text, recipient_name)
    except InputValidationError as e:
        log(f"入力検証エラー: {e}", "ERROR")
        raise

    anonymizer = get_anonymizer()
    anon_result: Optional[AnonymizationResult] = None

    # 匿名化処理
    if use_anonymization:
        anon_result = anonymizer.anonymize_text(validated_text)
        prompt_text = anon_result.anonymized_text
        log(f"匿名化完了: {anon_result.stats['total_pii_count']}件のPIIを検出・置換")

        # 受給者名も匿名化
        if validated_name:
            name_anon = anonymizer.anonymize_text(validated_name)
            anon_name = name_anon.anonymized_text
            # マッピングを統合
            anon_result.pii_mappings.extend(name_anon.pii_mappings)
            prompt_text = f"【対象受給者: {anon_name}】\n\n{prompt_text}"
        else:
            prompt_text = prompt_text
    else:
        prompt_text = validated_text
        if validated_name:
            prompt_text = f"【対象受給者: {validated_name}】\n\n{validated_text}"

    agent = get_agent()

    try:
        log(f"テキスト抽出開始（{len(prompt_text)}文字）{'[匿名化済み]' if use_anonymization else ''}")
        response = agent.run(
            f"以下のケース記録・報告書から情報を抽出してJSON形式で出力してください：\n\n{prompt_text}"
        )

        extracted = parse_json_from_response(response.content)

        if extracted:
            # 匿名化を使用した場合は復元処理
            if use_anonymization and anon_result:
                extracted = anonymizer.restore_data(extracted, anon_result.pii_mappings)
                log("データ復元完了")

            # 追記モードの場合、受給者名を設定
            if validated_name and extracted.get('recipient'):
                extracted['recipient']['name'] = validated_name

            name = extracted.get('recipient', {}).get('name', '不明')
            log(f"抽出成功: 受給者={name}")

            # 抽出サマリーをログ出力
            _log_extraction_summary(extracted)

            return extracted, anon_result

        log("JSONパース失敗: AIレスポンスからJSONを抽出できませんでした", "WARN")
        return None, anon_result

    except Exception as e:
        log(f"抽出エラー: {type(e).__name__}: {e}", "ERROR")
        return None, anon_result


def anonymize_text_for_external_ai(text: str) -> tuple[str, AnonymizationResult]:
    """
    外部AI送信用にテキストを匿名化

    TECHNICAL_STANDARDS.md Section 8.1 準拠

    Args:
        text: 匿名化対象のテキスト

    Returns:
        (匿名化されたテキスト, 匿名化結果)

    Usage:
        # 匿名化
        anonymized_text, result = anonymize_text_for_external_ai(text)

        # 外部AIに送信
        ai_response = external_ai.process(anonymized_text)

        # 復元
        restored_response = restore_text_from_external_ai(ai_response, result)
    """
    anonymizer = get_anonymizer()
    result = anonymizer.anonymize_text(text)
    log(f"テキスト匿名化完了: {result.stats['total_pii_count']}件のPIIを検出")
    return result.anonymized_text, result


def restore_text_from_external_ai(
    text: str,
    anon_result: AnonymizationResult
) -> str:
    """
    外部AIからの応答を復元（再識別）

    TECHNICAL_STANDARDS.md Section 8.2 準拠

    Args:
        text: 匿名化されたテキスト（AIからの応答）
        anon_result: 匿名化時の結果

    Returns:
        復元されたテキスト
    """
    anonymizer = get_anonymizer()
    restored = anonymizer.restore_text(text, anon_result.pii_mappings)
    log("テキスト復元完了")
    return restored


def get_anonymization_stats(text: str) -> dict:
    """
    テキスト内のPII統計情報を取得（匿名化は行わない）

    Args:
        text: 分析対象のテキスト

    Returns:
        PII統計情報
    """
    anonymizer = get_anonymizer()
    matches = anonymizer.detect_pii(text)

    type_counts = {}
    for match in matches:
        type_name = match.pii_type.value
        type_counts[type_name] = type_counts.get(type_name, 0) + 1

    return {
        "total_pii_count": len(matches),
        "pii_by_type": type_counts,
        "details": [
            {
                "type": m.pii_type.value,
                "preview": m.original[:10] + "..." if len(m.original) > 10 else m.original,
                "confidence": m.confidence
            }
            for m in matches
        ]
    }
