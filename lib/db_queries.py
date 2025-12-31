"""
生活保護受給者尊厳支援データベース - データ取得・検索モジュール
Manifesto: Livelihood Protection Support & Dignity Graph 準拠

受給者情報の取得、検索、サマリー生成
7本柱のスキーマに基づくデータ取得（Version 1.4対応）
"""

from .db_connection import run_query


# =============================================================================
# 基本取得関数
# =============================================================================

def get_recipients_list() -> list:
    """登録済み受給者一覧を取得"""
    return [r['name'] for r in run_query(
        "MATCH (r:Recipient) RETURN r.name as name ORDER BY r.name"
    )]


def get_recipient_stats() -> dict:
    """受給者統計情報を取得"""
    recipient_count = run_query("MATCH (n:Recipient) RETURN count(n) as c")[0]['c']

    ng_by_recipient = run_query("""
        MATCH (r:Recipient)
        OPTIONAL MATCH (r)-[:MUST_AVOID]->(ng:NgApproach)
        RETURN r.name as name, count(ng) as ng_count
        ORDER BY r.name
    """)

    mental_health_count = run_query("""
        MATCH (r:Recipient)-[:HAS_CONDITION]->(mh:MentalHealthStatus)
        RETURN count(DISTINCT r) as c
    """)[0]['c']

    economic_risk_count = run_query("""
        MATCH (r:Recipient)-[:FACES_RISK]->(er:EconomicRisk)
        WHERE er.status = 'Active'
        RETURN count(DISTINCT r) as c
    """)[0]['c']

    return {
        'recipient_count': recipient_count,
        'ng_by_recipient': ng_by_recipient,
        'mental_health_count': mental_health_count,
        'economic_risk_count': economic_risk_count
    }


# =============================================================================
# プロフィール取得
# =============================================================================

def get_recipient_profile(recipient_name: str) -> dict:
    """受給者のプロフィールを取得（引き継ぎ用・7本柱対応）"""

    # 避けるべき関わり方（最優先）
    ng_approaches = run_query("""
        MATCH (r:Recipient {name: $name})-[:MUST_AVOID]->(ng:NgApproach)
        RETURN ng.description as description, ng.reason as reason,
               ng.riskLevel as riskLevel, ng.consequence as consequence
        ORDER BY ng.riskLevel DESC
    """, {"name": recipient_name})

    # 経済的リスク
    economic_risks = run_query("""
        MATCH (r:Recipient {name: $name})-[:FACES_RISK]->(er:EconomicRisk)
        WHERE er.status = 'Active'
        RETURN er.type as type, er.perpetrator as perpetrator,
               er.perpetratorRelationship as relationship,
               er.severity as severity, er.description as description
        ORDER BY CASE er.severity WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END
    """, {"name": recipient_name})

    # 精神疾患の状況
    mental_health = run_query("""
        MATCH (r:Recipient {name: $name})-[:HAS_CONDITION]->(mh:MentalHealthStatus)
        RETURN mh.diagnosis as diagnosis, mh.currentStatus as status,
               mh.symptoms as symptoms, mh.treatmentStatus as treatment
    """, {"name": recipient_name})

    # 金銭管理状況
    money_status = run_query("""
        MATCH (r:Recipient {name: $name})-[:HAS_MONEY_STATUS]->(mms:MoneyManagementStatus)
        RETURN mms.capability as capability, mms.pattern as pattern,
               mms.riskLevel as riskLevel, mms.observations as observations
    """, {"name": recipient_name})

    # 日常生活自立支援事業
    daily_life_support = run_query("""
        MATCH (r:Recipient {name: $name})-[:USES_SERVICE]->(dlss:DailyLifeSupportService)
        RETURN dlss.socialWelfareCouncil as swc, dlss.services as services,
               dlss.status as status, dlss.specialist as specialist
    """, {"name": recipient_name})

    # 効果的だった関わり方
    effective_approaches = run_query("""
        MATCH (r:Recipient {name: $name})-[:RESPONDS_WELL_TO]->(ea:EffectiveApproach)
        RETURN ea.description as description, ea.context as context
    """, {"name": recipient_name})

    # 強み
    strengths = run_query("""
        MATCH (r:Recipient {name: $name})-[:HAS_STRENGTH]->(s:Strength)
        RETURN s.description as description, s.context as context
    """, {"name": recipient_name})

    # 最近のケース記録
    recent_records = run_query("""
        MATCH (r:Recipient {name: $name})-[:HAS_RECORD]->(cr:CaseRecord)
        RETURN cr.date as date, cr.category as category,
               cr.content as content, cr.recipientResponse as response
        ORDER BY cr.date DESC
        LIMIT 5
    """, {"name": recipient_name})

    # 連携機関
    support_orgs = run_query("""
        MATCH (r:Recipient {name: $name})-[:RECEIVES_SUPPORT_FROM]->(so:SupportOrganization)
        RETURN so.name as name, so.type as type, so.contactPerson as contact
    """, {"name": recipient_name})

    return {
        "recipient_name": recipient_name,
        "ng_approaches": ng_approaches,
        "economic_risks": economic_risks,
        "mental_health": mental_health[0] if mental_health else None,
        "money_status": money_status[0] if money_status else None,
        "daily_life_support": daily_life_support[0] if daily_life_support else None,
        "effective_approaches": effective_approaches,
        "strengths": strengths,
        "recent_records": recent_records,
        "support_organizations": support_orgs
    }


# =============================================================================
# サマリー生成
# =============================================================================

def get_handover_summary(recipient_name: str) -> str:
    """引き継ぎ用サマリーを生成（マニフェストルール4準拠・7本柱対応）"""
    profile = get_recipient_profile(recipient_name)

    lines = [f"# {recipient_name}さん 引き継ぎサマリー", ""]

    # 1. 避けるべき関わり方（最初に警告）
    if profile['ng_approaches']:
        lines.append("## ⚠️ 避けるべき関わり方")
        for ng in profile['ng_approaches']:
            risk_emoji = {"High": "🔴", "Medium": "🟠", "Low": "🟡"}.get(ng['riskLevel'], "⚪")
            lines.append(f"- {risk_emoji} **{ng['description']}**")
            if ng['reason']:
                lines.append(f"  - 理由: {ng['reason']}")
        lines.append("")

    # 2. 経済的リスク
    if profile['economic_risks']:
        lines.append("## ⚠️ 経済的リスク")
        for er in profile['economic_risks']:
            sev_emoji = {"High": "🔴", "Medium": "🟠", "Low": "🟡"}.get(er['severity'], "⚪")
            lines.append(f"- {sev_emoji} **{er['type']}**")
            if er['perpetrator']:
                lines.append(f"  - 加害者: {er['perpetrator']}（{er.get('relationship', '')}）")
            if er['description']:
                lines.append(f"  - 状況: {er['description']}")
        lines.append("")

    # 3. 精神疾患の状況
    if profile['mental_health']:
        mh = profile['mental_health']
        lines.append("## 🏥 精神疾患の状況")
        lines.append(f"- 診断: {mh['diagnosis']}")
        lines.append(f"- 現在の状態: {mh['status']}")
        lines.append(f"- 治療状況: {mh['treatment']}")
        lines.append("")

    # 4. 効果的だった関わり方
    if profile['effective_approaches']:
        lines.append("## ✅ 効果的だった関わり方")
        for ea in profile['effective_approaches']:
            lines.append(f"- {ea['description']}")
            if ea['context']:
                lines.append(f"  - 状況: {ea['context']}")
        lines.append("")

    # 5. 強み
    if profile['strengths']:
        lines.append("## 💪 発見された強み")
        for s in profile['strengths']:
            lines.append(f"- {s['description']}")
        lines.append("")

    # 6. 金銭管理状況と支援サービス
    if profile['money_status'] or profile['daily_life_support']:
        lines.append("## 💰 金銭管理と支援サービス")

        if profile['money_status']:
            ms = profile['money_status']
            lines.append(f"- 金銭管理能力: {ms['capability']}")
            if ms['pattern']:
                lines.append(f"- パターン: {ms['pattern']}")

        if profile['daily_life_support']:
            dlss = profile['daily_life_support']
            lines.append(f"- 日常生活自立支援事業: {dlss['status']}")
            lines.append(f"  - 社協: {dlss['swc']}")
            if dlss['services']:
                services = dlss['services']
                lines.append(f"  - サービス: {', '.join(services) if isinstance(services, list) else services}")
            if dlss['specialist']:
                lines.append(f"  - 担当: {dlss['specialist']}")
        lines.append("")

    # 7. 連携機関
    if profile['support_organizations']:
        lines.append("## 🤝 連携機関")
        for org in profile['support_organizations']:
            lines.append(f"- {org['name']}（{org['type']}）")
            if org['contact']:
                lines.append(f"  - 担当: {org['contact']}")
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# 類似案件検索・パターンマッチング
# =============================================================================

def search_similar_cases(recipient_name: str) -> list:
    """類似したリスクを持つ過去のケースを検索"""
    return run_query("""
        MATCH (target:Recipient {name: $name})-[:FACES_RISK]->(er:EconomicRisk)
        WITH collect(er.type) as targetRiskTypes

        MATCH (other:Recipient)-[:FACES_RISK]->(otherRisk:EconomicRisk)
        WHERE other.name <> $name
          AND otherRisk.type IN targetRiskTypes
        OPTIONAL MATCH (other)-[:USES_SERVICE]->(dlss:DailyLifeSupportService)

        RETURN DISTINCT
               other.name as 類似ケース,
               collect(DISTINCT otherRisk.type) as 共通リスク,
               dlss.services as 利用サービス,
               otherRisk.status as リスク状態
    """, {"name": recipient_name})


def find_matching_patterns(recipient_name: str) -> list:
    """受給者の状況に合致するパターンを検索"""
    return run_query("""
        MATCH (r:Recipient {name: $name})
        OPTIONAL MATCH (r)-[:FACES_RISK]->(er:EconomicRisk)
        OPTIONAL MATCH (r)-[:HAS_MONEY_STATUS]->(mms:MoneyManagementStatus)

        WITH r,
             collect(DISTINCT er.type) as riskTypes,
             mms.capability as moneyCapability

        MATCH (cp:CasePattern)
        WHERE any(indicator IN cp.indicators
                  WHERE indicator IN riskTypes
                     OR (moneyCapability IN ['困難', '支援が必要']
                         AND indicator CONTAINS '金銭管理'))

        RETURN cp.patternName as パターン名,
               cp.description as 説明,
               cp.recommendedInterventions as 推奨介入,
               cp.relatedServices as 関連サービス,
               cp.successfulCases as 成功件数
        ORDER BY cp.successfulCases DESC
    """, {"name": recipient_name})


# =============================================================================
# 訪問・連携関連
# =============================================================================

def get_visit_briefing(recipient_name: str) -> dict:
    """訪問前ブリーフィングを取得（安全情報を優先）"""
    results = run_query("""
        MATCH (r:Recipient {name: $name})

        OPTIONAL MATCH (r)-[:MUST_AVOID]->(ng:NgApproach)
        OPTIONAL MATCH (r)-[:FACES_RISK]->(er:EconomicRisk)
        WHERE er.status = 'Active'
        OPTIONAL MATCH (r)-[:HAS_CONDITION]->(mh:MentalHealthStatus)
        OPTIONAL MATCH (r)-[:HAS_MONEY_STATUS]->(mms:MoneyManagementStatus)
        OPTIONAL MATCH (r)-[:USES_SERVICE]->(dlss:DailyLifeSupportService)
        OPTIONAL MATCH (r)-[:RESPONDS_WELL_TO]->(ea:EffectiveApproach)

        RETURN r.name as 受給者名,
               collect(DISTINCT {
                 description: ng.description,
                 reason: ng.reason,
                 risk: ng.riskLevel
               }) as 避けるべき関わり方,
               collect(DISTINCT {
                 type: er.type,
                 perpetrator: er.perpetrator,
                 severity: er.severity
               }) as 経済的リスク,
               mh.diagnosis as 精神疾患,
               mh.currentStatus as 疾患の状態,
               mms.capability as 金銭管理能力,
               mms.pattern as 金銭管理パターン,
               dlss.services as 自立支援サービス,
               collect(DISTINCT {
                 description: ea.description,
                 context: ea.context
               }) as 効果的な関わり方
    """, {"name": recipient_name})
    return results[0] if results else {}


def get_collaboration_history(recipient_name: str, limit: int = 10) -> list:
    """多機関連携の履歴を取得"""
    return run_query("""
        MATCH (cr:CollaborationRecord)-[:ABOUT]->(r:Recipient {name: $name})
        OPTIONAL MATCH (cr)-[:INVOLVED]->(so:SupportOrganization)
        RETURN cr.date as 日付,
               cr.type as 種別,
               cr.participants as 参加者,
               cr.decisions as 決定事項,
               cr.nextActions as 次回アクション,
               collect(so.name) as 関係機関
        ORDER BY cr.date DESC
        LIMIT $limit
    """, {"name": recipient_name, "limit": limit})
