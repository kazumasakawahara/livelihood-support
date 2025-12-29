"""
生活保護受給者尊厳支援データベース - MCPサーバー
Manifesto: Livelihood Protection Support & Dignity Graph 準拠（Version 1.4）

Claude Desktop連携用MCPサーバー
二次被害防止と経済的安全を最優先とした情報提供

使用方法:
  uv run mcp/server.py
"""

import sys
import os
from datetime import date, datetime
from typing import Optional

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

# libモジュールをインポート
from lib.db_connection import run_query
from lib.db_queries import (
    get_recipients_list,
    get_recipient_profile,
    get_handover_summary,
    get_visit_briefing,
    get_collaboration_history,
    search_similar_cases,
    find_matching_patterns,
)
from lib.db_operations import (
    register_case_record,
    register_economic_risk,
    register_money_management_status,
    register_collaboration_record,
    register_ng_approach,
    register_effective_approach,
    register_support_organization,
)
from lib.audit import create_audit_log
from lib.ai_extractor import (
    extract_from_text,
    detect_critical_expressions,
    detect_economic_risk_signals,
    detect_collaboration_signals,
)

# MCPサーバー初期化
mcp = FastMCP("livelihood-support-db")


# =============================================================================
# ★★★★★ 最重要ツール（二次被害防止・経済的安全）
# =============================================================================

@mcp.tool()
def search_emergency_info(client_name: str, situation: str = "") -> dict:
    """
    【緊急時専用】クライアントの安全に関わる情報を優先順位付きで取得します。
    
    ★ AI運用プロトコル「Safety First」に基づき、以下の順序で情報を返します:
    1. NgApproach(禁忌事項)- 二次被害を防ぐため最優先
    2. EconomicRisk(経済的リスク)- 搾取からの保護
    3. EffectiveApproach(効果的な対処)- その場を落ち着かせるため
    4. MentalHealthStatus(精神疾患)
    5. KeyPerson(緊急連絡先)- ランク順
    6. Hospital(かかりつけ医)
    
    Args:
        client_name: クライアントの名前(部分一致可)
        situation: 状況キーワード(例: 'パニック', '食事', '入浴')※任意
    
    Returns:
        優先順位付きの緊急対応情報(JSON形式)
    """
    result = run_query("""
        MATCH (r:Recipient)
        WHERE r.name CONTAINS $name
        
        // 1. 避けるべき関わり方（最優先）
        OPTIONAL MATCH (r)-[:MUST_AVOID]->(ng:NgApproach)
        
        // 2. 経済的リスク
        OPTIONAL MATCH (r)-[:FACES_RISK]->(er:EconomicRisk)
        WHERE er.status = 'Active'
        
        // 3. 効果的な関わり方
        OPTIONAL MATCH (r)-[:RESPONDS_WELL_TO]->(ea:EffectiveApproach)
        
        // 4. 精神疾患
        OPTIONAL MATCH (r)-[:HAS_CONDITION]->(mh:MentalHealthStatus)
        
        // 5. キーパーソン
        OPTIONAL MATCH (r)-[kp_rel:HAS_KEY_PERSON]->(kp:KeyPerson)
        
        // 6. 医療機関
        OPTIONAL MATCH (r)-[:TREATED_AT]->(mi:MedicalInstitution)
        
        RETURN r.name as recipient_name,
               collect(DISTINCT {
                   description: ng.description,
                   reason: ng.reason,
                   riskLevel: ng.riskLevel
               }) as ng_approaches,
               collect(DISTINCT {
                   type: er.type,
                   perpetrator: er.perpetrator,
                   severity: er.severity,
                   description: er.description
               }) as economic_risks,
               collect(DISTINCT {
                   description: ea.description,
                   context: ea.context
               }) as effective_approaches,
               {
                   diagnosis: mh.diagnosis,
                   status: mh.currentStatus,
                   treatment: mh.treatmentStatus
               } as mental_health,
               collect(DISTINCT {
                   name: kp.name,
                   relationship: kp.relationship,
                   contact: kp.contactInfo,
                   rank: kp_rel.rank
               }) as key_persons,
               collect(DISTINCT {
                   name: mi.name,
                   department: mi.department,
                   doctor: mi.doctor
               }) as hospitals
    """, {"name": client_name})
    
    if not result:
        return {"error": f"受給者 '{client_name}' が見つかりません"}
    
    data = result[0]
    
    # 空のエントリをフィルタリング
    data['ng_approaches'] = [x for x in data['ng_approaches'] if x.get('description')]
    data['economic_risks'] = [x for x in data['economic_risks'] if x.get('type')]
    data['effective_approaches'] = [x for x in data['effective_approaches'] if x.get('description')]
    data['key_persons'] = sorted(
        [x for x in data['key_persons'] if x.get('name')],
        key=lambda x: x.get('rank', 99)
    )
    data['hospitals'] = [x for x in data['hospitals'] if x.get('name')]
    
    return {
        "recipient_name": data['recipient_name'],
        "priority_order": "NgApproach → EconomicRisk → EffectiveApproach → MentalHealth → KeyPerson → Hospital",
        "ng_approaches": data['ng_approaches'],
        "economic_risks": data['economic_risks'],
        "effective_approaches": data['effective_approaches'],
        "mental_health": data['mental_health'] if data['mental_health'].get('diagnosis') else None,
        "key_persons": data['key_persons'],
        "hospitals": data['hospitals']
    }


@mcp.tool()
def get_visit_briefing_tool(recipient_name: str) -> dict:
    """
    訪問前ブリーフィングを取得します。
    
    ★★★★★ 二次被害防止の要 ★★★★★
    
    訪問前に必ず確認すべき情報を優先順位付きで提供します：
    1. ⚠️ 避けるべき関わり方（NgApproach）
    2. ⚠️ 経済的リスク（EconomicRisk）
    3. 🏥 精神疾患の状況
    4. 💰 金銭管理状況と支援サービス
    5. ✅ 効果的だった関わり方
    
    Args:
        recipient_name: 受給者名（部分一致可）
    
    Returns:
        訪問前ブリーフィング情報（JSON形式）
    """
    result = get_visit_briefing(recipient_name)
    
    if not result:
        return {"error": f"受給者 '{recipient_name}' が見つかりません"}
    
    return result[0] if result else {}


@mcp.tool()
def detect_critical_guidance(case_record_text: str) -> dict:
    """
    ケース記録から批判的な指導表現を検出します。
    
    ★ 二次被害防止のための重要ツール ★
    
    「指導した」「約束させた」「就労を促した」などの表現を検出し、
    より適切な表現への変換を提案します。
    
    また、経済的リスクのサインも同時に検出します。
    
    Args:
        case_record_text: ケース記録のテキスト
    
    Returns:
        検出された批判的表現と推奨変換、経済的リスクサイン
    """
    critical = detect_critical_expressions(case_record_text)
    economic = detect_economic_risk_signals(case_record_text)
    collaboration = detect_collaboration_signals(case_record_text)
    
    warnings = []
    
    if critical:
        warnings.append("⚠️ 批判的な表現が検出されました。本人の尊厳を守る表現への変換を検討してください。")
    
    if economic:
        warnings.append("⚠️ 経済的リスクのサインが検出されました。詳細を確認してください。")
    
    return {
        "critical_expressions": critical,
        "economic_risk_signals": economic,
        "collaboration_signals": collaboration,
        "warnings": warnings,
        "recommendation": "精神疾患のある方への『指導』は二次被害のリスクがあります。" if critical else None
    }


# =============================================================================
# ★★★★☆ 重要ツール（引き継ぎ支援）
# =============================================================================

@mcp.tool()
def get_handover_summary_tool(recipient_name: str) -> str:
    """
    引き継ぎ用サマリーを生成します（マニフェストルール4準拠）。
    
    担当者交代時に新担当者へ渡す情報を優先順位付きで提供：
    1. ⚠️ 避けるべき関わり方（最初に警告）
    2. ⚠️ 経済的リスク（搾取リスクがある場合）
    3. 🏥 精神疾患の状況
    4. ✅ 効果的だった関わり方
    5. 💪 発見された強み
    6. 💰 金銭管理状況と支援サービス
    7. 🤝 連携している機関
    
    Args:
        recipient_name: 受給者名
    
    Returns:
        Markdown形式の引き継ぎサマリー
    """
    return get_handover_summary(recipient_name)


@mcp.tool()
def get_client_profile(client_name: str) -> dict:
    """
    クライアントの全体像（プロフィール）を取得します。
    
    マニフェストの7本柱すべての情報を統合して返します:
    - 第1の柱：ケース記録
    - 第2の柱：抽出された本人像
    - 第3の柱：関わり方の知恵（効果と禁忌）
    - 第4の柱：参考情報としての申告歴
    - 第5の柱：社会的ネットワーク
    - 第6の柱：法的・制度的基盤
    - 第7の柱：金銭的安全と多機関連携
    
    Args:
        client_name: クライアントの名前(部分一致可)
    
    Returns:
        クライアントの包括的なプロフィール情報
    """
    return get_recipient_profile(client_name)


# =============================================================================
# ★★★★☆ 重要ツール（記録と分析）
# =============================================================================

@mcp.tool()
def add_support_log(client_name: str, narrative_text: str) -> dict:
    """
    支援記録を物語風テキストから自動抽出して登録します。

    日常の支援内容を自由なテキストで記録し、AIが自動的に構造化データとして保存します。
    「今日〜した」「〜の対応で落ち着いた」などの表現から、支援記録を抽出します。
    
    ★ 経済的リスクのサインも自動検出します ★

    Args:
        client_name: クライアント名
        narrative_text: 支援記録の物語風テキスト(例: 「今日、健太さんがパニックを起こしたので、静かに見守りました。5分で落ち着きました。」)

    Returns:
        登録結果のメッセージ

    使用例:
        - 「山田健太さんの支援記録を追加: 今日の訪問で、急な音に驚いてパニックになりました。テレビを消して静かにしたら、5分で落ち着きました。この対応は効果的でした。」
        - 「佐々木真理さんの記録: 後ろから声をかけたらパニックになった。次からは必ず視界に入ってから話しかけるようにします。」
        - 「田中さんの記録: 『お金がない』との訴え。受給日から3日しか経っていない。息子が来てお金を持っていったとのこと。」
    """
    # 経済的リスクサインの事前検出
    economic_signals = detect_economic_risk_signals(narrative_text)
    critical_signals = detect_critical_expressions(narrative_text)
    
    # AIで構造化
    extracted = extract_from_text(narrative_text, recipient_name=client_name)
    
    if not extracted:
        return {"status": "error", "message": "テキストからの情報抽出に失敗しました"}
    
    # ケース記録として登録
    if extracted.get('caseRecords'):
        for record in extracted['caseRecords']:
            register_case_record(record, client_name)
    
    # 経済的リスクがあれば登録
    if extracted.get('economicRisks'):
        for risk in extracted['economicRisks']:
            register_economic_risk(risk, client_name)
    
    # 金銭管理状況があれば登録
    if extracted.get('moneyManagementStatus', {}).get('capability'):
        register_money_management_status(extracted['moneyManagementStatus'], client_name)
    
    # 連携記録があれば登録
    if extracted.get('collaborationRecords'):
        for collab in extracted['collaborationRecords']:
            register_collaboration_record(collab, client_name)
    
    # 監査ログ
    create_audit_log("mcp_user", "ADD_SUPPORT_LOG", "CaseRecord", client_name)
    
    result = {
        "status": "success",
        "message": f"{client_name}さんの支援記録を登録しました",
        "extracted_items": []
    }
    
    if extracted.get('caseRecords'):
        result['extracted_items'].append(f"ケース記録: {len(extracted['caseRecords'])}件")
    if extracted.get('economicRisks'):
        result['extracted_items'].append(f"⚠️経済的リスク: {len(extracted['economicRisks'])}件")
    if extracted.get('ngApproaches'):
        result['extracted_items'].append(f"⚠️避けるべき関わり方: {len(extracted['ngApproaches'])}件")
    if extracted.get('effectiveApproaches'):
        result['extracted_items'].append(f"効果的な関わり方: {len(extracted['effectiveApproaches'])}件")
    
    if economic_signals:
        result['warnings'] = ["⚠️ 経済的リスクのサインが検出されました。詳細を確認してください。"]
        result['economic_signals'] = economic_signals
    
    if critical_signals:
        result['critical_expressions'] = critical_signals
    
    return result


@mcp.tool()
def get_support_logs(client_name: str, limit: int = 10) -> list:
    """
    クライアントの支援記録履歴を取得します。

    過去の支援内容と効果を時系列で確認できます。
    効果的だった対応を参考にしたり、逆効果だった対応を避けるために使用します。

    Args:
        client_name: クライアント名
        limit: 取得件数(デフォルト: 10件、最大50件)

    Returns:
        支援記録の履歴(JSON形式)

    使用例:
        - 「山田健太さんの最近の支援記録を見せて」
        - 「佐々木真理さんの過去20件の支援記録」
    """
    if limit > 50:
        limit = 50
    
    return run_query("""
        MATCH (r:Recipient)-[:HAS_RECORD]->(cr:CaseRecord)
        WHERE r.name CONTAINS $name
        RETURN cr.date as date,
               cr.category as category,
               cr.content as content,
               cr.recipientResponse as response,
               cr.caseworker as caseworker
        ORDER BY cr.date DESC
        LIMIT $limit
    """, {"name": client_name, "limit": limit})


@mcp.tool()
def discover_care_patterns(client_name: str, min_frequency: int = 2) -> list:
    """
    効果的だった支援パターンを発見します。

    複数回効果があった対応方法を自動検出し、ベストプラクティスとして提示します。
    経験知を蓄積し、新しい支援者への引き継ぎに活用できます。

    Args:
        client_name: クライアント名
        min_frequency: 最小出現回数(デフォルト: 2回以上)

    Returns:
        発見されたパターンのリスト(JSON形式)

    使用例:
        - 「山田健太さんの効果的なケアパターンを教えて」
        - 「佐々木真理さんで3回以上効果があった対応方法は?」
    """
    return run_query("""
        MATCH (r:Recipient {name: $name})-[:RESPONDS_WELL_TO]->(ea:EffectiveApproach)
        WHERE ea.frequency IS NOT NULL OR size(ea.sourceRecords) >= $min_freq
        RETURN ea.description as pattern,
               ea.context as context,
               ea.frequency as frequency
        ORDER BY ea.frequency DESC
    """, {"name": client_name, "min_freq": min_frequency})


# =============================================================================
# ★★★★☆ 重要ツール（類似案件・パターンマッチング）
# =============================================================================

@mcp.tool()
def find_similar_cases(recipient_name: str) -> dict:
    """
    類似したリスクを持つ過去のケースを検索します。
    
    同様の経済的リスクや金銭管理課題を持つケースを発見し、
    効果的だった介入方法を参考にできます。
    
    Args:
        recipient_name: 受給者名
    
    Returns:
        類似ケースのリストと効果的だった介入
    """
    similar = search_similar_cases(recipient_name)
    patterns = find_matching_patterns(recipient_name)
    
    return {
        "similar_cases": similar,
        "matching_patterns": patterns,
        "recommendation": "類似ケースで効果的だった介入を参考に、支援計画を検討してください。"
    }


@mcp.tool()
def get_collaboration_history_tool(recipient_name: str, limit: int = 10) -> list:
    """
    多機関連携の履歴を取得します。
    
    ケース会議、情報共有、合同対応などの記録を時系列で確認できます。
    
    Args:
        recipient_name: 受給者名
        limit: 取得件数（デフォルト: 10件）
    
    Returns:
        連携記録のリスト
    """
    return get_collaboration_history(recipient_name, limit)


# =============================================================================
# ★★★☆☆ 管理系ツール
# =============================================================================

@mcp.tool()
def check_renewal_dates(days_ahead: int = 90, client_name: str = "") -> list:
    """
    手帳・受給者証の更新期限が近いクライアントを検索します。
    
    期限管理は権利擁護の基本です。更新漏れは本人の不利益に直結します。
    
    Args:
        days_ahead: 何日先までをチェックするか(デフォルト: 90日)
        client_name: 特定のクライアントのみ検索する場合に指定(任意)
    
    Returns:
        更新期限が近い証明書のリスト
    """
    query = """
        MATCH (r:Recipient)-[:HOLDS]->(c:Certificate)
        WHERE c.expiryDate IS NOT NULL
          AND c.expiryDate <= date() + duration({days: $days})
          AND c.expiryDate >= date()
    """
    
    if client_name:
        query += " AND r.name CONTAINS $name"
    
    query += """
        RETURN r.name as recipient,
               c.type as certificate_type,
               c.grade as grade,
               toString(c.expiryDate) as expiry_date,
               duration.inDays(date(), c.expiryDate).days as days_until_expiry
        ORDER BY c.expiryDate
    """
    
    return run_query(query, {"days": days_ahead, "name": client_name})


@mcp.tool()
def list_clients() -> dict:
    """
    登録されているすべてのクライアントの一覧と、各クライアントの情報登録状況を取得します。

    Returns:
        クライアント一覧と登録状況のサマリー(年齢表示付き)
    """
    recipients = run_query("""
        MATCH (r:Recipient)
        OPTIONAL MATCH (r)-[:MUST_AVOID]->(ng:NgApproach)
        OPTIONAL MATCH (r)-[:FACES_RISK]->(er:EconomicRisk)
        WHERE er IS NULL OR er.status = 'Active'
        OPTIONAL MATCH (r)-[:HAS_CONDITION]->(mh:MentalHealthStatus)
        OPTIONAL MATCH (r)-[:USES_SERVICE]->(dlss:DailyLifeSupportService)
        RETURN r.name as name,
               r.dob as dob,
               count(DISTINCT ng) as ng_count,
               count(DISTINCT er) as economic_risk_count,
               mh.diagnosis as mental_health,
               dlss.status as daily_life_support
        ORDER BY r.name
    """)
    
    # 年齢計算
    today = date.today()
    for r in recipients:
        if r.get('dob'):
            try:
                dob = r['dob']
                if hasattr(dob, 'year'):
                    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                    r['age'] = age
            except:
                r['age'] = None
    
    return {
        "total_count": len(recipients),
        "recipients": recipients
    }


@mcp.tool()
def get_audit_logs(client_name: str = "", user_name: str = "", limit: int = 30) -> list:
    """
    監査ログ(操作履歴)を取得します。

    誰が・いつ・何を変更したかを確認できます。
    権利擁護の観点から、データの変更履歴を追跡するために使用します。

    Args:
        client_name: クライアント名でフィルタ(任意、部分一致)
        user_name: 操作者名でフィルタ(任意、部分一致)
        limit: 取得件数(デフォルト: 30件、最大100件)

    Returns:
        監査ログの一覧(JSON形式)

    使用例:
        - 「最近の操作履歴を見せて」
        - 「山田健太さんに関する変更履歴」
        - 「田中さんが行った操作一覧」
    """
    if limit > 100:
        limit = 100
    
    query = "MATCH (al:AuditLog) WHERE 1=1"
    params = {"limit": limit}
    
    if client_name:
        query += " AND al.recipientName CONTAINS $client_name"
        params["client_name"] = client_name
    
    if user_name:
        query += " AND al.user CONTAINS $user_name"
        params["user_name"] = user_name
    
    query += """
        RETURN al.timestamp as timestamp,
               al.user as user,
               al.action as action,
               al.targetType as target_type,
               al.targetName as target_name,
               al.details as details,
               al.recipientName as recipient
        ORDER BY al.timestamp DESC
        LIMIT $limit
    """
    
    return run_query(query, params)


@mcp.tool()
def get_database_stats() -> dict:
    """
    データベース全体の統計情報を取得します。
    各ノードタイプの登録数、リレーション数などを確認できます。
    
    Returns:
        データベースの統計情報
    """
    node_counts = run_query("""
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        ORDER BY count DESC
    """)
    
    rel_counts = run_query("""
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
    """)
    
    # 重要な統計
    recipients_with_risk = run_query("""
        MATCH (r:Recipient)
        OPTIONAL MATCH (r)-[:FACES_RISK]->(er:EconomicRisk {status: 'Active'})
        OPTIONAL MATCH (r)-[:MUST_AVOID]->(ng:NgApproach)
        OPTIONAL MATCH (r)-[:HAS_CONDITION]->(mh:MentalHealthStatus)
        WITH r, 
             count(DISTINCT er) as economic_risks,
             count(DISTINCT ng) as ng_approaches,
             mh.diagnosis as mental_health
        RETURN count(r) as total_recipients,
               sum(CASE WHEN economic_risks > 0 THEN 1 ELSE 0 END) as with_economic_risk,
               sum(CASE WHEN ng_approaches > 0 THEN 1 ELSE 0 END) as with_ng_approaches,
               sum(CASE WHEN mental_health IS NOT NULL THEN 1 ELSE 0 END) as with_mental_health
    """)[0]
    
    return {
        "node_counts": {item['label']: item['count'] for item in node_counts},
        "relationship_counts": {item['type']: item['count'] for item in rel_counts},
        "summary": {
            "total_recipients": recipients_with_risk['total_recipients'],
            "with_economic_risk": recipients_with_risk['with_economic_risk'],
            "with_ng_approaches": recipients_with_risk['with_ng_approaches'],
            "with_mental_health": recipients_with_risk['with_mental_health']
        }
    }


@mcp.tool()
def get_client_change_history(client_name: str, limit: int = 20) -> list:
    """
    特定クライアントに関する変更履歴を取得します。

    クライアントの情報がいつ・誰によって変更されたかを時系列で確認できます。
    引き継ぎ時や問題発生時の原因調査に活用できます。

    Args:
        client_name: クライアント名
        limit: 取得件数(デフォルト: 20件)

    Returns:
        変更履歴(JSON形式)

    使用例:
        - 「山田健太さんの変更履歴を確認」
        - 「佐々木さんのデータ更新履歴」
    """
    return run_query("""
        MATCH (al:AuditLog)
        WHERE al.recipientName CONTAINS $name
        RETURN al.timestamp as timestamp,
               al.user as user,
               al.action as action,
               al.targetType as target_type,
               al.targetName as target_name,
               al.details as details
        ORDER BY al.timestamp DESC
        LIMIT $limit
    """, {"name": client_name, "limit": limit})


@mcp.tool()
def run_cypher_query(cypher: str) -> list:
    """
    カスタムCypherクエリを実行します。

    ⚠️ 読み取り専用クエリのみ実行可能です。
    データの変更（CREATE, MERGE, SET, DELETE）は許可されていません。

    Args:
        cypher: 実行するCypherクエリ

    Returns:
        クエリ結果
    """
    # 書き込み操作を禁止
    dangerous_keywords = ['CREATE', 'MERGE', 'SET', 'DELETE', 'REMOVE', 'DROP', 'DETACH']
    upper_cypher = cypher.upper()

    for keyword in dangerous_keywords:
        if keyword in upper_cypher:
            return {"error": f"書き込み操作 '{keyword}' は許可されていません。読み取りクエリのみ実行可能です。"}

    try:
        return run_query(cypher)
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# ★★★★★ 直接登録ツール（構造化データ登録）
# =============================================================================

@mcp.tool()
def register_ng_approach_tool(
    recipient_name: str,
    description: str,
    reason: str = "",
    risk_level: str = "Medium",
    consequence: str = ""
) -> dict:
    """
    避けるべき関わり方を直接登録します。

    ★★★★★ 二次被害防止の最重要データ ★★★★★

    この情報は訪問前ブリーフィングや引き継ぎサマリーで最優先表示されます。

    Args:
        recipient_name: 受給者名
        description: 避けるべき関わり方の内容
            例: 「大きな声で話しかける」「背後から近づく」「お金の話題」
        reason: なぜ避けるべきかの理由
            例: 「パニックを誘発する」「トラウマに触れる」
        risk_level: リスクレベル（High/Medium/Low）
            デフォルト: Medium
        consequence: 実際に起きた結果（任意）
            例: 「パニック発作を起こした」

    Returns:
        登録結果

    使用例:
        - 「山田さんに『大きな声での会話』を禁忌として登録。理由: パニック誘発、リスク: High」
        - 「佐藤さんに『お金の話題をすぐ持ち出す』をNG登録。理由: 過去のトラウマ」
    """
    ng_data = {
        "description": description,
        "reason": reason,
        "riskLevel": risk_level,
        "consequence": consequence
    }

    result = register_ng_approach(ng_data, recipient_name, "mcp_user")

    create_audit_log("mcp_user", "CREATE", "NgApproach", description, recipient_name=recipient_name)

    return {
        "status": result.get("status", "success"),
        "message": f"⚠️ 避けるべき関わり方を登録しました: {description}",
        "recipient": recipient_name,
        "risk_level": risk_level,
        "warning": "この情報は訪問前ブリーフィングで最優先表示されます"
    }


@mcp.tool()
def register_economic_risk_tool(
    recipient_name: str,
    risk_type: str,
    perpetrator: str = "",
    perpetrator_relationship: str = "",
    severity: str = "Medium",
    description: str = "",
    status: str = "Active"
) -> dict:
    """
    経済的リスクを登録します。

    ★★★★★ 経済的搾取からの保護 ★★★★★

    家族や知人からの金銭搾取リスクを記録します。

    Args:
        recipient_name: 受給者名
        risk_type: リスクの種類
            例: 「経済的搾取」「金銭持ち出し」「借金の強要」「名義貸し」
        perpetrator: 加害者名（任意）
        perpetrator_relationship: 加害者との関係
            例: 「長男」「元夫」「知人」
        severity: 深刻度（High/Medium/Low）
        description: 詳細説明
        status: 状態（Active/Resolved/Monitoring）

    Returns:
        登録結果

    使用例:
        - 「山田さん: 長男による経済的搾取リスク。毎月訪問してお金を持っていく。深刻度High」
        - 「佐藤さん: 知人から借金を申し込まれている。状態を監視中」
    """
    risk_data = {
        "type": risk_type,
        "perpetrator": perpetrator,
        "perpetratorRelationship": perpetrator_relationship,
        "severity": severity,
        "description": description,
        "status": status
    }

    result = register_economic_risk(risk_data, recipient_name, "mcp_user")

    return {
        "status": result.get("status", "success"),
        "message": f"⚠️ 経済的リスクを登録しました: {risk_type}",
        "recipient": recipient_name,
        "severity": severity,
        "perpetrator": perpetrator if perpetrator else "未特定",
        "warning": "このリスクは訪問前ブリーフィングで警告表示されます"
    }


@mcp.tool()
def register_money_management_tool(
    recipient_name: str,
    capability: str,
    pattern: str = "",
    risk_level: str = "Low",
    observations: str = ""
) -> dict:
    """
    金銭管理状況を登録します。

    本人の金銭管理能力とパターンを記録し、日常生活自立支援事業の
    必要性判断に活用します。

    Args:
        recipient_name: 受給者名
        capability: 金銭管理能力
            例: 「自己管理可能」「支援が必要」「要見守り」「困難」
        pattern: 金銭管理パターン
            例: 「受給日に使い切る」「計画的に使用」「貯蓄あり」
        risk_level: リスクレベル（High/Medium/Low）
        observations: 観察所見

    Returns:
        登録結果

    使用例:
        - 「山田さんの金銭管理: 支援が必要、受給日に使い切る傾向、リスク中」
        - 「佐藤さん: 自己管理可能だが、息子の訪問後にお金がなくなる傾向」
    """
    mms_data = {
        "capability": capability,
        "pattern": pattern,
        "riskLevel": risk_level,
        "observations": observations
    }

    result = register_money_management_status(mms_data, recipient_name, "mcp_user")

    return {
        "status": result.get("status", "success"),
        "message": f"金銭管理状況を登録しました: {capability}",
        "recipient": recipient_name,
        "capability": capability,
        "risk_level": risk_level
    }


@mcp.tool()
def register_effective_approach_tool(
    recipient_name: str,
    description: str,
    context: str = "",
    frequency: str = ""
) -> dict:
    """
    効果的だった関わり方を登録します。

    本人に対して効果的だった対応方法を記録し、
    支援者間で共有できるようにします。

    Args:
        recipient_name: 受給者名
        description: 効果的だった関わり方の内容
            例: 「ゆっくり話しかける」「視界に入ってから声をかける」
        context: どのような状況で効果的だったか
            例: 「パニック時」「訪問時」
        frequency: 効果の頻度（任意）
            例: 「毎回効果あり」「時々効果あり」

    Returns:
        登録結果

    使用例:
        - 「山田さん: テレビを消して静かな環境にすると落ち着く」
        - 「佐藤さん: 絵を褒めると会話がスムーズになる」
    """
    approach_data = {
        "description": description,
        "context": context,
        "frequency": frequency
    }

    result = register_effective_approach(approach_data, recipient_name, "mcp_user")

    create_audit_log("mcp_user", "CREATE", "EffectiveApproach", description, recipient_name=recipient_name)

    return {
        "status": result.get("status", "success"),
        "message": f"✅ 効果的な関わり方を登録しました: {description}",
        "recipient": recipient_name,
        "context": context if context else "一般"
    }


@mcp.tool()
def register_support_org_tool(
    recipient_name: str,
    org_name: str,
    org_type: str = "その他",
    contact_person: str = "",
    phone: str = "",
    services: str = "",
    status: str = "利用中"
) -> dict:
    """
    連携支援機関を登録します。

    受給者を支援している機関や組織を記録し、
    多機関連携の基盤を構築します。

    Args:
        recipient_name: 受給者名
        org_name: 機関名
            例: 「○○社会福祉協議会」「△△作業所」「□□地域包括支援センター」
        org_type: 機関の種類
            例: 「社会福祉協議会」「障害福祉サービス」「医療機関」「地域包括」
        contact_person: 担当者名
        phone: 電話番号
        services: 提供サービス
        status: 利用状況（利用中/利用終了/調整中）

    Returns:
        登録結果

    使用例:
        - 「山田さんの連携機関: 〇〇社会福祉協議会、日常生活自立支援事業利用中」
        - 「佐藤さん: △△作業所で週3回通所」
    """
    org_data = {
        "name": org_name,
        "type": org_type,
        "contactPerson": contact_person,
        "phone": phone,
        "services": services,
        "utilizationStatus": status
    }

    result = register_support_organization(org_data, recipient_name, "mcp_user")

    create_audit_log("mcp_user", "CREATE", "SupportOrganization", org_name, recipient_name=recipient_name)

    return {
        "status": result.get("status", "success"),
        "message": f"🤝 連携機関を登録しました: {org_name}",
        "recipient": recipient_name,
        "org_type": org_type,
        "status": status
    }


# =============================================================================
# MCPプロンプト（ガイダンス）
# =============================================================================

@mcp.prompt()
def visit_preparation(recipient_name: str) -> str:
    """
    訪問前の準備を支援するプロンプト
    """
    return f"""
# 訪問前チェックリスト: {recipient_name}さん

訪問前に以下を必ず確認してください：

## 1. 緊急確認事項
- `get_visit_briefing_tool("{recipient_name}")` を実行して最新のブリーフィングを取得

## 2. 確認すべき重要項目
1. ⚠️ 避けるべき関わり方（NgApproach）
2. ⚠️ 経済的リスク（EconomicRisk）
3. 🏥 精神疾患の状況
4. 💰 金銭管理状況
5. ✅ 効果的だった関わり方

## 3. 訪問時の注意
- 本人のペースを尊重する
- 「指導」ではなく「支援」の姿勢で
- 経済的搾取のサインに注意

## 4. 訪問後の記録
- 訪問記録は `add_support_log` で登録可能
- 新たな気づきがあれば随時登録を
"""


@mcp.prompt()
def handover_guide(recipient_name: str) -> str:
    """
    引き継ぎを支援するプロンプト
    """
    return f"""
# 担当者引き継ぎガイド: {recipient_name}さん

## 1. 引き継ぎサマリーの取得
```
get_handover_summary_tool("{recipient_name}")
```

## 2. 優先確認事項（マニフェストルール4準拠）
1. ⚠️ 避けるべき関わり方を最初に確認
2. ⚠️ 経済的リスクの状況
3. 🏥 精神疾患と現在の状態
4. ✅ 効果的だった関わり方
5. 💪 発見された強み
6. 💰 金銭管理状況
7. 🤝 連携している機関

## 3. 注意事項
- 過去の記録は「観察事実」として扱う
- 本人の自己決定を尊重
- 経済的リスクがある場合は特に注意

## 4. 前任者への確認ポイント
- 最近の変化や気になる点
- 特に効果的だった対応
- 注意が必要な状況
"""


@mcp.prompt()
def risk_assessment_guide(recipient_name: str) -> str:
    """
    リスクアセスメントを支援するプロンプト
    """
    return f"""
# リスクアセスメントガイド: {recipient_name}さん

## 1. 現在のリスク情報取得
```
search_emergency_info("{recipient_name}")
```

## 2. 経済的リスクの評価

### チェックポイント:
- [ ] 家族や知人からの金銭要求はないか
- [ ] 受給日から数日で金銭がなくなっていないか
- [ ] 必要な支出ができているか
- [ ] 借金の申し込みを受けていないか
- [ ] 名義貸しを求められていないか

### リスクサインの例:
- 「お金がない」との訴えが受給日直後にある
- 特定の人物の訪問後にお金がなくなる
- 食費を切り詰めている様子がある

## 3. 必要に応じて登録
- 経済的リスク: `register_economic_risk_tool`
- 金銭管理状況: `register_money_management_tool`

## 4. 類似ケースの参照
```
find_similar_cases("{recipient_name}")
```
過去の類似ケースで効果的だった介入を参考に
"""


@mcp.prompt()
def case_recording_guide() -> str:
    """
    ケース記録の書き方ガイド
    """
    return """
# ケース記録ガイド（尊厳支援の視点）

## 1. 避けるべき表現

### ❌ 使わない方がよい表現:
- 「指導した」「指示した」
- 「約束させた」「誓わせた」
- 「就労を促した」「働くよう伝えた」
- 「言い聞かせた」「説諭した」

### ✅ 推奨される表現:
- 「お伝えした」「ご案内した」
- 「確認した」「相談した」
- 「一緒に検討した」「選択肢を提示した」
- 「意向を確認した」「お話を伺った」

## 2. 記録の視点

### 本人の強みに注目:
- できていること、頑張っていることを記録
- 本人なりの工夫や対処を認める

### 観察と解釈を分ける:
- 「元気がなかった」→「普段より発話が少なかった」
- 「怒っていた」→「声を荒げて話していた」

## 3. 経済的リスクのサイン

以下のサインに気づいたら記録と登録を:
- 「お金がない」との訴え（受給日からの日数も記録）
- 特定人物の訪問・連絡の後の変化
- 必要な支出ができていない様子

## 4. 記録の登録
`add_support_log("受給者名", "記録内容")` で自動構造化登録
"""


# =============================================================================
# MCPリソース（参照データ）
# =============================================================================

@mcp.resource("recipients://list")
def get_recipients_resource() -> str:
    """登録されている受給者の一覧"""
    recipients = get_recipients_list()
    return "\n".join([f"- {name}" for name in recipients])


@mcp.resource("stats://overview")
def get_stats_resource() -> str:
    """データベースの統計情報"""
    stats = run_query("""
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        ORDER BY count DESC
    """)
    lines = ["# データベース統計", ""]
    for item in stats:
        lines.append(f"- {item['label']}: {item['count']}件")
    return "\n".join(lines)


@mcp.resource("guide://manifesto")
def get_manifesto_guide() -> str:
    """マニフェストの概要ガイド"""
    return """
# 生活保護受給者尊厳支援グラフ マニフェスト概要

## 7本柱のスキーマ

### 第1の柱：ケース記録
- CaseRecord: 日々の支援記録
- HomeVisit: 家庭訪問記録
- Observation: 観察事実

### 第2の柱：抽出された本人像
- Strength: 強み
- Challenge: 課題
- Pattern: 行動パターン
- MentalHealthStatus: 精神疾患の状況

### 第3の柱：関わり方の知恵
- EffectiveApproach: 効果的だった関わり方
- NgApproach: 避けるべき関わり方（最重要）
- TriggerSituation: 注意が必要な状況

### 第4の柱：参考情報としての申告歴
- DeclaredHistory: 申告された生活歴
- PathwayToProtection: 保護に至った経緯
- Wish: 本人の願い

### 第5の柱：社会的ネットワーク
- KeyPerson: キーパーソン
- FamilyMember: 家族
- SupportOrganization: 支援機関
- MedicalInstitution: 医療機関

### 第6の柱：法的・制度的基盤
- ProtectionDecision: 保護決定
- Certificate: 証明書・手帳
- SupportGoal: 支援目標

### 第7の柱：金銭的安全と多機関連携
- MoneyManagementStatus: 金銭管理状況
- EconomicRisk: 経済的リスク
- DailyLifeSupportService: 日常生活自立支援事業
- CollaborationRecord: 多機関連携記録
- CasePattern: 類似案件パターン

## 5つのAI運用プロトコル

1. **Safety First（二次被害防止最優先）**
   - NgApproachを常に最優先で確認・表示

2. **Interpretation Humility（解釈の謙虚さ）**
   - 申告歴は「参考情報」として扱い断定しない

3. **Temporal Awareness（時間軸への配慮）**
   - 状況は変化することを前提にする

4. **Handover Support（引き継ぎ支援）**
   - 新担当者への優先順位付き情報提供

5. **Financial Safety（金銭的安全の確保）**
   - 経済的リスクのサインを検出し警告
"""


@mcp.resource("guide://economic-risk")
def get_economic_risk_guide() -> str:
    """経済的リスクの検出ガイド"""
    return """
# 経済的リスク検出ガイド

## リスクの種類

### 1. 経済的搾取
- 家族や知人による金銭の持ち出し
- 受給日を狙った訪問
- 「立て替え」「借り」の要求

### 2. 借金・名義貸し
- 借金の保証人になることの要求
- クレジットカードの名義貸し
- 携帯電話契約の名義貸し

### 3. 詐欺・悪質商法
- 高額商品の押し売り
- 不必要なリフォーム
- 投資詐欺

## 検出のサイン

### 言動のサイン
- 「お金がない」（受給日から日が浅い場合）
- 「○○が来たら払わなきゃ」
- 「息子に送らなきゃ」

### 状況のサイン
- 受給日直後の金銭不足
- 特定人物訪問後の変化
- 食費の切り詰め
- 公共料金の滞納

### 関係性のサイン
- 頻繁な家族の訪問（特に受給日前後）
- 「頼まれた」「断れない」という発言
- 知らない人からの連絡増加

## 対応のポイント

1. **本人の意向を確認**
   - 強制せず、選択肢を提示

2. **関係機関との連携**
   - 社会福祉協議会（日常生活自立支援事業）
   - 地域包括支援センター
   - 警察（被害が明確な場合）

3. **記録の重要性**
   - 日付と状況を正確に
   - 本人の発言は「 」で記録
"""


# =============================================================================
# サーバー起動
# =============================================================================

if __name__ == "__main__":
    mcp.run()
