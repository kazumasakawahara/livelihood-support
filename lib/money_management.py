"""
生活保護受給者尊厳支援データベース - 金銭管理・多機関連携モジュール
Manifesto: Livelihood Protection Support & Dignity Graph 準拠

金銭管理困難、経済的虐待、日常生活自立支援事業、多機関連携に関する
データ操作を提供
"""

import os
import sys
from datetime import date, datetime
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()


# --- ログ出力 ---
def log(message: str, level: str = "INFO"):
    sys.stderr.write(f"[MoneyManagement:{level}] {message}\n")
    sys.stderr.flush()


# --- Neo4j 接続（db_operationsと共有） ---
from .db_operations import run_query, create_audit_log


# =============================================================================
# 金銭管理状況 (MoneyManagementStatus)
# =============================================================================

def register_money_management_status(
    status_data: dict, 
    recipient_name: str, 
    user_name: str = "system"
) -> dict:
    """
    金銭管理の状況を登録
    
    Args:
        status_data: {
            'capability': '自己管理可能/支援あり/困難',
            'pattern': '浪費パターンの説明',
            'riskLevel': 'High/Medium/Low',
            'triggers': ['給料日直後', '月末'],
            'observations': '観察された具体的な状況'
        }
    """
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        MERGE (mms:MoneyManagementStatus {recipientName: $recipient_name})
        SET mms.capability = $capability,
            mms.pattern = $pattern,
            mms.riskLevel = $risk_level,
            mms.triggers = $triggers,
            mms.observations = $observations,
            mms.assessmentDate = date($assessment_date),
            mms.updatedAt = datetime()
        MERGE (r)-[:HAS_MONEY_STATUS]->(mms)
        RETURN mms.capability as capability, mms.riskLevel as riskLevel
    """, {
        "recipient_name": recipient_name,
        "capability": status_data.get('capability', '未評価'),
        "pattern": status_data.get('pattern', ''),
        "risk_level": status_data.get('riskLevel', 'Medium'),
        "triggers": status_data.get('triggers', []),
        "observations": status_data.get('observations', ''),
        "assessment_date": status_data.get('assessmentDate', date.today().isoformat())
    })
    
    create_audit_log(
        user_name=user_name,
        action="CREATE",
        target_type="MoneyManagementStatus",
        target_name=f"{status_data.get('capability', '')} - {status_data.get('riskLevel', '')}",
        details=status_data.get('pattern', ''),
        recipient_name=recipient_name
    )
    
    return {"status": "success", "data": result[0] if result else {}}


def get_money_management_status(recipient_name: str) -> dict:
    """金銭管理状況を取得"""
    result = run_query("""
        MATCH (r:Recipient {name: $name})-[:HAS_MONEY_STATUS]->(mms:MoneyManagementStatus)
        RETURN mms.capability as capability,
               mms.pattern as pattern,
               mms.riskLevel as riskLevel,
               mms.triggers as triggers,
               mms.observations as observations,
               mms.assessmentDate as assessmentDate
    """, {"name": recipient_name})
    
    return result[0] if result else None


# =============================================================================
# 経済的リスク (EconomicRisk) - 虐待・搾取を含む
# =============================================================================

ECONOMIC_RISK_TYPES = [
    "金銭搾取",           # 親族等による金銭の搾取
    "無心・たかり",        # 繰り返しの金銭要求
    "通帳管理強要",        # 通帳・カードの管理を強要
    "借金の肩代わり強要",   # 本人に借金を負わせる
    "年金・手当の横領",     # 受給している年金等の横領
    "住居費の搾取",        # 家賃等を不当に徴収
    "詐欺被害リスク",       # 詐欺に遭いやすい状況
    "浪費",              # 自身による浪費
    "その他"
]


def register_economic_risk(
    risk_data: dict,
    recipient_name: str,
    user_name: str = "system"
) -> dict:
    """
    経済的リスクを登録
    
    Args:
        risk_data: {
            'type': '金銭搾取/無心・たかり/通帳管理強要/...',
            'perpetrator': '加害者（親族名など）',
            'perpetratorRelationship': '続柄',
            'severity': 'High/Medium/Low',
            'description': '具体的な状況',
            'discoveredDate': '発見日',
            'status': 'Active/Monitoring/Resolved',
            'interventions': ['実施した介入']
        }
    """
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        CREATE (er:EconomicRisk {
            type: $type,
            perpetrator: $perpetrator,
            perpetratorRelationship: $relationship,
            severity: $severity,
            description: $description,
            discoveredDate: date($discovered_date),
            status: $status,
            interventions: $interventions,
            createdAt: datetime()
        })
        CREATE (r)-[:FACES_RISK]->(er)
        
        // 加害者が家族の場合、家族ノードともリレーション
        WITH r, er
        OPTIONAL MATCH (fm:FamilyMember {name: $perpetrator})<-[:HAS_FAMILY]-(r)
        FOREACH (_ IN CASE WHEN fm IS NOT NULL THEN [1] ELSE [] END |
            MERGE (fm)-[:POSES_RISK]->(er)
        )
        
        RETURN er.type as type, er.severity as severity
    """, {
        "recipient_name": recipient_name,
        "type": risk_data.get('type', 'その他'),
        "perpetrator": risk_data.get('perpetrator', ''),
        "relationship": risk_data.get('perpetratorRelationship', ''),
        "severity": risk_data.get('severity', 'Medium'),
        "description": risk_data.get('description', ''),
        "discovered_date": risk_data.get('discoveredDate', date.today().isoformat()),
        "status": risk_data.get('status', 'Active'),
        "interventions": risk_data.get('interventions', [])
    })
    
    # 重要な安全情報として詳細にログ
    create_audit_log(
        user_name=user_name,
        action="CREATE",
        target_type="EconomicRisk",
        target_name=f"⚠️{risk_data.get('type', '')} - {risk_data.get('perpetrator', '不明')}",
        details=f"深刻度: {risk_data.get('severity', '')}, 状況: {risk_data.get('description', '')}",
        recipient_name=recipient_name
    )
    
    log(f"⚠️ 経済的リスク登録: {risk_data.get('type', '')} (深刻度: {risk_data.get('severity', '')})")
    
    return {"status": "success", "data": result[0] if result else {}}


def get_economic_risks(recipient_name: str) -> list:
    """経済的リスク一覧を取得"""
    return run_query("""
        MATCH (r:Recipient {name: $name})-[:FACES_RISK]->(er:EconomicRisk)
        OPTIONAL MATCH (fm:FamilyMember)-[:POSES_RISK]->(er)
        RETURN er.type as type,
               er.perpetrator as perpetrator,
               er.perpetratorRelationship as relationship,
               er.severity as severity,
               er.description as description,
               er.status as status,
               er.interventions as interventions,
               fm.name as familyMemberName
        ORDER BY 
            CASE er.severity WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
            er.discoveredDate DESC
    """, {"name": recipient_name})


def get_active_economic_risks(recipient_name: str) -> list:
    """アクティブな経済的リスクのみ取得（訪問前確認用）"""
    return run_query("""
        MATCH (r:Recipient {name: $name})-[:FACES_RISK]->(er:EconomicRisk)
        WHERE er.status = 'Active'
        RETURN er.type as type,
               er.perpetrator as perpetrator,
               er.severity as severity,
               er.description as description
        ORDER BY 
            CASE er.severity WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END
    """, {"name": recipient_name})


# =============================================================================
# 日常生活自立支援事業 (DailyLifeSupportService)
# =============================================================================

DAILY_LIFE_SUPPORT_SERVICES = [
    "福祉サービス利用援助",      # 福祉サービスの利用手続き支援
    "日常的金銭管理サービス",    # 預金の払い戻し、公共料金の支払い等
    "書類等預かりサービス",      # 通帳、年金証書等の預かり
]


def register_daily_life_support_service(
    service_data: dict,
    recipient_name: str,
    user_name: str = "system"
) -> dict:
    """
    日常生活自立支援事業の利用を登録
    
    Args:
        service_data: {
            'socialWelfareCouncil': '○○市社会福祉協議会',
            'startDate': '利用開始日',
            'services': ['日常的金銭管理サービス', '書類等預かりサービス'],
            'frequency': '月2回',
            'specialist': '担当専門員名',
            'contactInfo': '連絡先',
            'status': '利用中/利用終了/申請中',
            'referralRoute': '地域包括支援センター経由',
            'reason': '利用理由'
        }
    """
    # 社会福祉協議会をSupportOrganizationとして登録
    run_query("""
        MERGE (so:SupportOrganization {name: $council_name})
        SET so.type = '社会福祉協議会',
            so.services = '日常生活自立支援事業',
            so.updatedAt = datetime()
    """, {"council_name": service_data.get('socialWelfareCouncil', '')})
    
    # 日常生活自立支援事業の利用を登録
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        MATCH (so:SupportOrganization {name: $council_name})
        
        CREATE (dlss:DailyLifeSupportService {
            startDate: date($start_date),
            services: $services,
            frequency: $frequency,
            specialist: $specialist,
            contactInfo: $contact,
            status: $status,
            referralRoute: $referral,
            reason: $reason,
            createdAt: datetime()
        })
        
        CREATE (r)-[:USES_SERVICE]->(dlss)
        CREATE (dlss)-[:PROVIDED_BY]->(so)
        
        // 経済的リスクとの関連付け（緩和策として）
        WITH r, dlss
        OPTIONAL MATCH (r)-[:FACES_RISK]->(er:EconomicRisk)
        WHERE er.status = 'Active'
        FOREACH (_ IN CASE WHEN er IS NOT NULL THEN [1] ELSE [] END |
            MERGE (er)-[:MITIGATED_BY]->(dlss)
        )
        
        RETURN dlss.services as services, dlss.status as status
    """, {
        "recipient_name": recipient_name,
        "council_name": service_data.get('socialWelfareCouncil', ''),
        "start_date": service_data.get('startDate', date.today().isoformat()),
        "services": service_data.get('services', []),
        "frequency": service_data.get('frequency', ''),
        "specialist": service_data.get('specialist', ''),
        "contact": service_data.get('contactInfo', ''),
        "status": service_data.get('status', '利用中'),
        "referral": service_data.get('referralRoute', ''),
        "reason": service_data.get('reason', '')
    })
    
    create_audit_log(
        user_name=user_name,
        action="CREATE",
        target_type="DailyLifeSupportService",
        target_name=service_data.get('socialWelfareCouncil', ''),
        details=f"サービス: {', '.join(service_data.get('services', []))}",
        recipient_name=recipient_name
    )
    
    return {"status": "success", "data": result[0] if result else {}}


def get_daily_life_support_service(recipient_name: str) -> dict:
    """日常生活自立支援事業の利用状況を取得"""
    result = run_query("""
        MATCH (r:Recipient {name: $name})-[:USES_SERVICE]->(dlss:DailyLifeSupportService)
        OPTIONAL MATCH (dlss)-[:PROVIDED_BY]->(so:SupportOrganization)
        RETURN dlss.services as services,
               dlss.frequency as frequency,
               dlss.specialist as specialist,
               dlss.contactInfo as contactInfo,
               dlss.status as status,
               dlss.reason as reason,
               so.name as socialWelfareCouncil
    """, {"name": recipient_name})
    
    return result[0] if result else None


# =============================================================================
# 多機関連携記録 (CollaborationRecord)
# =============================================================================

def register_collaboration_record(
    collab_data: dict,
    recipient_name: str,
    user_name: str = "system"
) -> dict:
    """
    多機関連携記録を登録
    
    Args:
        collab_data: {
            'date': '開催日',
            'type': 'ケース会議/情報共有/緊急対応/定期連絡',
            'participants': [
                {'name': '田中', 'organization': '福祉事務所', 'role': 'ケースワーカー'},
                {'name': '佐藤', 'organization': '地域包括支援センター', 'role': '相談員'},
                {'name': '鈴木', 'organization': '社会福祉協議会', 'role': '専門員'}
            ],
            'agenda': '議題',
            'discussion': '協議内容',
            'decisions': ['決定事項1', '決定事項2'],
            'nextActions': [
                {'action': 'アクション', 'responsible': '担当者', 'deadline': '期限'}
            ]
        }
    """
    # 参加機関をSupportOrganizationとして登録
    for p in collab_data.get('participants', []):
        if p.get('organization'):
            run_query("""
                MERGE (so:SupportOrganization {name: $org_name})
                SET so.updatedAt = datetime()
            """, {"org_name": p['organization']})
    
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        
        CREATE (cr:CollaborationRecord {
            date: date($date),
            type: $type,
            participants: $participants,
            agenda: $agenda,
            discussion: $discussion,
            decisions: $decisions,
            nextActions: $next_actions,
            createdBy: $user_name,
            createdAt: datetime()
        })
        
        CREATE (cr)-[:ABOUT]->(r)
        
        RETURN cr.date as date, cr.type as type
    """, {
        "recipient_name": recipient_name,
        "date": collab_data.get('date', date.today().isoformat()),
        "type": collab_data.get('type', 'ケース会議'),
        "participants": [p.get('name', '') + '(' + p.get('organization', '') + ')' 
                        for p in collab_data.get('participants', [])],
        "agenda": collab_data.get('agenda', ''),
        "discussion": collab_data.get('discussion', ''),
        "decisions": collab_data.get('decisions', []),
        "next_actions": [f"{a.get('action', '')} - {a.get('responsible', '')} ({a.get('deadline', '')})" 
                        for a in collab_data.get('nextActions', [])],
        "user_name": user_name
    })
    
    # 参加機関とのリレーション
    for p in collab_data.get('participants', []):
        if p.get('organization'):
            run_query("""
                MATCH (cr:CollaborationRecord)-[:ABOUT]->(r:Recipient {name: $recipient_name})
                WHERE cr.date = date($date)
                MATCH (so:SupportOrganization {name: $org_name})
                MERGE (cr)-[:INVOLVED]->(so)
            """, {
                "recipient_name": recipient_name,
                "date": collab_data.get('date', date.today().isoformat()),
                "org_name": p['organization']
            })
    
    create_audit_log(
        user_name=user_name,
        action="CREATE",
        target_type="CollaborationRecord",
        target_name=f"{collab_data.get('type', '')} - {collab_data.get('date', '')}",
        details=collab_data.get('agenda', ''),
        recipient_name=recipient_name
    )
    
    return {"status": "success", "data": result[0] if result else {}}


def get_collaboration_records(recipient_name: str, limit: int = 10) -> list:
    """多機関連携記録を取得"""
    return run_query("""
        MATCH (cr:CollaborationRecord)-[:ABOUT]->(r:Recipient {name: $name})
        RETURN cr.date as date,
               cr.type as type,
               cr.participants as participants,
               cr.agenda as agenda,
               cr.decisions as decisions,
               cr.nextActions as nextActions
        ORDER BY cr.date DESC
        LIMIT $limit
    """, {"name": recipient_name, "limit": limit})


# =============================================================================
# 類似案件パターン (CasePattern)
# =============================================================================

def register_case_pattern(pattern_data: dict, user_name: str = "system") -> dict:
    """
    類似案件パターンを登録（ナレッジとして蓄積）
    
    Args:
        pattern_data: {
            'patternName': 'パターン名（例：親族による金銭搾取）',
            'description': 'パターンの説明',
            'indicators': ['指標1', '指標2'],  # このパターンを示す兆候
            'riskFactors': ['リスク要因1', 'リスク要因2'],
            'recommendedInterventions': ['推奨される介入1', '介入2'],
            'successfulCases': 3,  # このパターンで成功した件数
            'relatedServices': ['日常生活自立支援事業', '成年後見制度']
        }
    """
    result = run_query("""
        MERGE (cp:CasePattern {patternName: $pattern_name})
        SET cp.description = $description,
            cp.indicators = $indicators,
            cp.riskFactors = $risk_factors,
            cp.recommendedInterventions = $interventions,
            cp.successfulCases = $successful_cases,
            cp.relatedServices = $related_services,
            cp.updatedAt = datetime()
        RETURN cp.patternName as patternName
    """, {
        "pattern_name": pattern_data.get('patternName', ''),
        "description": pattern_data.get('description', ''),
        "indicators": pattern_data.get('indicators', []),
        "risk_factors": pattern_data.get('riskFactors', []),
        "interventions": pattern_data.get('recommendedInterventions', []),
        "successful_cases": pattern_data.get('successfulCases', 0),
        "related_services": pattern_data.get('relatedServices', [])
    })
    
    return {"status": "success", "data": result[0] if result else {}}


def match_case_to_patterns(recipient_name: str) -> list:
    """
    受給者の状況から類似パターンを検索
    
    経済的リスク、金銭管理状況から類似パターンを発見
    """
    return run_query("""
        // 受給者の経済的リスクと金銭管理状況を取得
        MATCH (r:Recipient {name: $name})
        OPTIONAL MATCH (r)-[:FACES_RISK]->(er:EconomicRisk)
        OPTIONAL MATCH (r)-[:HAS_MONEY_STATUS]->(mms:MoneyManagementStatus)
        
        WITH r, 
             collect(DISTINCT er.type) as riskTypes,
             mms.capability as moneyCapability
        
        // 類似パターンを検索
        MATCH (cp:CasePattern)
        WHERE any(indicator IN cp.indicators 
                  WHERE indicator IN riskTypes 
                     OR (moneyCapability = '困難' AND indicator CONTAINS '金銭管理'))
        
        RETURN cp.patternName as patternName,
               cp.description as description,
               cp.recommendedInterventions as recommendedInterventions,
               cp.relatedServices as relatedServices,
               cp.successfulCases as successfulCases
        ORDER BY cp.successfulCases DESC
    """, {"name": recipient_name})


def link_recipient_to_pattern(
    recipient_name: str, 
    pattern_name: str,
    user_name: str = "system"
) -> dict:
    """受給者を類似パターンに紐付け"""
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        MATCH (cp:CasePattern {patternName: $pattern_name})
        MERGE (r)-[rel:MATCHES_PATTERN]->(cp)
        SET rel.linkedAt = datetime(),
            rel.linkedBy = $user_name
        RETURN cp.patternName as patternName
    """, {
        "recipient_name": recipient_name,
        "pattern_name": pattern_name,
        "user_name": user_name
    })
    
    return {"status": "success", "data": result[0] if result else {}}


# =============================================================================
# 統合クエリ：金銭管理に関する包括的な情報取得
# =============================================================================

def get_financial_safety_summary(recipient_name: str) -> dict:
    """
    金銭的安全に関する包括的なサマリーを取得
    訪問前ブリーフィングで使用
    """
    # 金銭管理状況
    money_status = get_money_management_status(recipient_name)
    
    # 経済的リスク（アクティブのみ）
    economic_risks = get_active_economic_risks(recipient_name)
    
    # 日常生活自立支援事業
    daily_life_support = get_daily_life_support_service(recipient_name)
    
    # 類似パターンと推奨介入
    matched_patterns = match_case_to_patterns(recipient_name)
    
    # 最近の連携記録
    recent_collaborations = get_collaboration_records(recipient_name, limit=3)
    
    return {
        "recipient_name": recipient_name,
        "money_management_status": money_status,
        "economic_risks": economic_risks,
        "daily_life_support_service": daily_life_support,
        "matched_patterns": matched_patterns,
        "recent_collaborations": recent_collaborations
    }


def find_similar_cases(recipient_name: str) -> list:
    """
    類似案件を検索
    同じ経済的リスクを持つ他のケースを発見
    """
    return run_query("""
        // 対象受給者の経済的リスクを取得
        MATCH (r:Recipient {name: $name})-[:FACES_RISK]->(er:EconomicRisk)
        WITH collect(er.type) as targetRiskTypes
        
        // 同じリスクタイプを持つ他の受給者を検索
        MATCH (other:Recipient)-[:FACES_RISK]->(otherRisk:EconomicRisk)
        WHERE other.name <> $name
          AND otherRisk.type IN targetRiskTypes
        
        // その受給者が利用しているサービスも取得
        OPTIONAL MATCH (other)-[:USES_SERVICE]->(dlss:DailyLifeSupportService)
        
        RETURN DISTINCT other.name as recipientName,
               collect(DISTINCT otherRisk.type) as sharedRisks,
               dlss.services as servicesUsed,
               dlss.status as serviceStatus
        LIMIT 10
    """, {"name": recipient_name})


def get_intervention_success_rate(intervention_type: str) -> dict:
    """
    特定の介入方法の成功率を取得
    例：日常生活自立支援事業の導入で経済的リスクが軽減されたケース
    """
    result = run_query("""
        // 日常生活自立支援事業を利用しているケース
        MATCH (r:Recipient)-[:USES_SERVICE]->(dlss:DailyLifeSupportService)
        WHERE $intervention IN dlss.services
        
        // そのケースの経済的リスクの状態を確認
        OPTIONAL MATCH (r)-[:FACES_RISK]->(er:EconomicRisk)
        
        WITH count(DISTINCT r) as totalCases,
             count(DISTINCT CASE WHEN er.status = 'Resolved' THEN r END) as resolvedCases,
             count(DISTINCT CASE WHEN er.status = 'Active' THEN r END) as activeCases
        
        RETURN totalCases,
               resolvedCases,
               activeCases,
               CASE WHEN totalCases > 0 
                    THEN toFloat(resolvedCases) / totalCases * 100 
                    ELSE 0 END as successRate
    """, {"intervention": intervention_type})
    
    return result[0] if result else {}
