"""
生活保護受給者尊厳支援データベース - データ登録モジュール
Manifesto: Livelihood Protection Support & Dignity Graph 準拠

7本柱のスキーマに基づくCRUD操作（Version 1.4対応）
"""

from datetime import date

from .db_connection import run_query, log
from .validation import ValidationError, validate_recipient_name
from .audit import create_audit_log


# =============================================================================
# 第1の柱：ケース記録（最重要）
# =============================================================================

def register_case_record(record_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """ケース記録を登録"""
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        CREATE (cr:CaseRecord {
            date: date($date),
            category: $category,
            content: $content,
            caseworker: $caseworker,
            recipientResponse: $response,
            createdAt: datetime()
        })
        CREATE (r)-[:HAS_RECORD]->(cr)

        WITH r, cr
        UNWIND $observations as obs
        CREATE (o:Observation {
            date: date($date),
            content: obs,
            reliability: 'Observed'
        })
        CREATE (cr)-[:OBSERVED]->(o)

        RETURN cr.date as date, cr.category as category
    """, {
        "recipient_name": recipient_name,
        "date": record_data.get('date', date.today().isoformat()),
        "category": record_data.get('category', 'その他'),
        "content": record_data.get('content', ''),
        "caseworker": record_data.get('caseworker', user_name),
        "response": record_data.get('recipientResponse', ''),
        "observations": record_data.get('observations', [])
    })

    create_audit_log(user_name, "CREATE", "CaseRecord",
                     f"{record_data.get('date', '')} - {record_data.get('category', '')}",
                     recipient_name=recipient_name)

    return {"status": "success", "data": result[0] if result else {}}


def register_home_visit(visit_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """家庭訪問記録を登録"""
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        CREATE (hv:HomeVisit {
            date: date($date),
            observations: $observations,
            recipientCondition: $condition,
            livingEnvironment: $environment,
            recipientMood: $mood,
            nextAction: $nextAction,
            caseworker: $caseworker,
            createdAt: datetime()
        })
        CREATE (r)-[:VISITED_ON]->(hv)
        RETURN hv.date as date
    """, {
        "recipient_name": recipient_name,
        "date": visit_data.get('date', date.today().isoformat()),
        "observations": visit_data.get('observations', ''),
        "condition": visit_data.get('recipientCondition', ''),
        "environment": visit_data.get('livingEnvironment', ''),
        "mood": visit_data.get('recipientMood', ''),
        "nextAction": visit_data.get('nextAction', ''),
        "caseworker": visit_data.get('caseworker', user_name)
    })

    return {"status": "success", "data": result[0] if result else {}}


# =============================================================================
# 第2の柱：抽出された本人像
# =============================================================================

def register_strength(strength_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """強みを登録"""
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        CREATE (s:Strength {
            description: $description,
            discoveredDate: date($discovered_date),
            context: $context,
            sourceRecord: $source,
            createdAt: datetime()
        })
        CREATE (r)-[:HAS_STRENGTH]->(s)
        RETURN s.description as description
    """, {
        "recipient_name": recipient_name,
        "description": strength_data.get('description', ''),
        "discovered_date": strength_data.get('discoveredDate', date.today().isoformat()),
        "context": strength_data.get('context', ''),
        "source": strength_data.get('sourceRecord', '')
    })

    return {"status": "success", "data": result[0] if result else {}}


def register_challenge(challenge_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """課題を登録"""
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        CREATE (ch:Challenge {
            description: $description,
            severity: $severity,
            currentStatus: $status,
            supportNeeded: $support,
            firstIdentified: date($first_date),
            createdAt: datetime()
        })
        CREATE (r)-[:FACES]->(ch)
        RETURN ch.description as description
    """, {
        "recipient_name": recipient_name,
        "description": challenge_data.get('description', ''),
        "severity": challenge_data.get('severity', 'Medium'),
        "status": challenge_data.get('currentStatus', 'Active'),
        "support": challenge_data.get('supportNeeded', ''),
        "first_date": challenge_data.get('firstIdentified', date.today().isoformat())
    })

    return {"status": "success", "data": result[0] if result else {}}


def register_mental_health_status(mh_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """精神疾患の状況を登録"""
    if not mh_data.get('diagnosis'):
        return {"status": "skipped", "message": "診断名なし"}

    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        MERGE (mh:MentalHealthStatus {diagnosis: $diagnosis})
        SET mh.currentStatus = $status,
            mh.symptoms = $symptoms,
            mh.treatmentStatus = $treatment,
            mh.lastAssessment = date($last_date),
            mh.updatedAt = datetime()
        MERGE (r)-[:HAS_CONDITION]->(mh)
        RETURN mh.diagnosis as diagnosis
    """, {
        "recipient_name": recipient_name,
        "diagnosis": mh_data.get('diagnosis', ''),
        "status": mh_data.get('currentStatus', ''),
        "symptoms": mh_data.get('symptoms', []),
        "treatment": mh_data.get('treatmentStatus', ''),
        "last_date": mh_data.get('lastAssessment', date.today().isoformat())
    })

    create_audit_log(user_name, "CREATE", "MentalHealthStatus", mh_data.get('diagnosis', ''),
                     recipient_name=recipient_name)

    return {"status": "success", "data": result[0] if result else {}}


def register_pattern(pattern_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """行動パターンを登録"""
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        CREATE (p:Pattern {
            description: $description,
            frequency: $frequency,
            triggers: $triggers,
            createdAt: datetime()
        })
        CREATE (r)-[:SHOWS_PATTERN]->(p)
        RETURN p.description as description
    """, {
        "recipient_name": recipient_name,
        "description": pattern_data.get('description', ''),
        "frequency": pattern_data.get('frequency', ''),
        "triggers": pattern_data.get('triggers', [])
    })

    return {"status": "success", "data": result[0] if result else {}}


# =============================================================================
# 第3の柱：関わり方の知恵（効果と禁忌）
# =============================================================================

def register_effective_approach(approach_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """効果的だった関わり方を登録"""
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        CREATE (ea:EffectiveApproach {
            description: $description,
            context: $context,
            frequency: $frequency,
            createdAt: datetime()
        })
        CREATE (r)-[:RESPONDS_WELL_TO]->(ea)
        RETURN ea.description as description
    """, {
        "recipient_name": recipient_name,
        "description": approach_data.get('description', ''),
        "context": approach_data.get('context', ''),
        "frequency": approach_data.get('frequency', '')
    })

    return {"status": "success", "data": result[0] if result else {}}


def register_ng_approach(ng_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """避けるべき関わり方を登録（最重要）"""
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        CREATE (ng:NgApproach {
            description: $description,
            reason: $reason,
            riskLevel: $risk,
            consequence: $consequence,
            createdAt: datetime()
        })
        CREATE (r)-[:MUST_AVOID]->(ng)
        RETURN ng.description as description, ng.riskLevel as risk
    """, {
        "recipient_name": recipient_name,
        "description": ng_data.get('description', ''),
        "reason": ng_data.get('reason', ''),
        "risk": ng_data.get('riskLevel', 'Medium'),
        "consequence": ng_data.get('consequence', '')
    })

    create_audit_log(user_name, "CREATE", "NgApproach", ng_data.get('description', ''),
                     details=f"リスク: {ng_data.get('riskLevel', '')}",
                     recipient_name=recipient_name)

    log(f"NgApproach登録: {ng_data.get('description', '')} (リスク: {ng_data.get('riskLevel', '')})")

    return {"status": "success", "data": result[0] if result else {}}


def register_trigger_situation(trigger_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """注意が必要な状況を登録"""
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        CREATE (ts:TriggerSituation {
            description: $description,
            signs: $signs,
            recommendedResponse: $response,
            createdAt: datetime()
        })
        CREATE (r)-[:HAS_TRIGGER]->(ts)
        RETURN ts.description as description
    """, {
        "recipient_name": recipient_name,
        "description": trigger_data.get('description', ''),
        "signs": trigger_data.get('signs', []),
        "response": trigger_data.get('recommendedResponse', '')
    })

    return {"status": "success", "data": result[0] if result else {}}


# =============================================================================
# 第4の柱：参考情報としての申告歴
# =============================================================================

def register_recipient(recipient_data: dict, user_name: str = "system") -> dict:
    """受給者基本情報を登録"""
    result = run_query("""
        MERGE (r:Recipient {name: $name})
        SET r.caseNumber = COALESCE($case_number, r.caseNumber),
            r.dob = CASE WHEN $dob IS NOT NULL THEN date($dob) ELSE r.dob END,
            r.gender = COALESCE($gender, r.gender),
            r.address = COALESCE($address, r.address),
            r.protectionStartDate = CASE WHEN $start_date IS NOT NULL
                THEN date($start_date) ELSE r.protectionStartDate END,
            r.updatedAt = datetime()
        RETURN r.name as name
    """, {
        "name": recipient_data.get('name', ''),
        "case_number": recipient_data.get('caseNumber'),
        "dob": recipient_data.get('dob'),
        "gender": recipient_data.get('gender'),
        "address": recipient_data.get('address'),
        "start_date": recipient_data.get('protectionStartDate')
    })

    create_audit_log(user_name, "CREATE", "Recipient", recipient_data.get('name', ''))

    return {"status": "success", "data": result[0] if result else {}}


def register_declared_history(history_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """申告された生活歴を登録"""
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        CREATE (dh:DeclaredHistory {
            era: $era,
            content: $content,
            reliability: 'Declared',
            declaredDate: date($declared_date),
            createdAt: datetime()
        })
        CREATE (r)-[:DECLARED_HISTORY]->(dh)
        RETURN dh.era as era
    """, {
        "recipient_name": recipient_name,
        "era": history_data.get('era', ''),
        "content": history_data.get('content', ''),
        "declared_date": history_data.get('declaredDate', date.today().isoformat())
    })

    return {"status": "success", "data": result[0] if result else {}}


def register_pathway_to_protection(pathway_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """保護に至った経緯を登録"""
    if not pathway_data.get('declaredTrigger'):
        return {"status": "skipped", "message": "経緯情報なし"}

    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        MERGE (p:PathwayToProtection {recipientName: $recipient_name})
        SET p.declaredTrigger = $trigger,
            p.declaredTimeline = $timeline,
            p.reliability = 'Declared',
            p.updatedAt = datetime()
        MERGE (r)-[:DECLARED_PATHWAY]->(p)
        RETURN p.declaredTrigger as trigger
    """, {
        "recipient_name": recipient_name,
        "trigger": pathway_data.get('declaredTrigger', ''),
        "timeline": pathway_data.get('declaredTimeline', '')
    })

    return {"status": "success", "data": result[0] if result else {}}


def register_wish(wish_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """本人の願いを登録"""
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        CREATE (w:Wish {
            content: $content,
            priority: $priority,
            declaredDate: date($declared_date),
            status: $status,
            createdAt: datetime()
        })
        CREATE (r)-[:WISHES]->(w)
        RETURN w.content as content
    """, {
        "recipient_name": recipient_name,
        "content": wish_data.get('content', ''),
        "priority": wish_data.get('priority', 'Medium'),
        "declared_date": wish_data.get('declaredDate', date.today().isoformat()),
        "status": wish_data.get('status', 'Active')
    })

    return {"status": "success", "data": result[0] if result else {}}


# =============================================================================
# 第5の柱：社会的ネットワーク
# =============================================================================

def register_key_person(kp_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """キーパーソンを登録"""
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        MERGE (kp:KeyPerson {name: $name})
        SET kp.relationship = $relationship,
            kp.contactInfo = $contact,
            kp.role = $role,
            kp.lastContact = $last_contact,
            kp.updatedAt = datetime()
        MERGE (r)-[rel:HAS_KEY_PERSON]->(kp)
        SET rel.rank = $rank
        RETURN kp.name as name, rel.rank as rank
    """, {
        "recipient_name": recipient_name,
        "name": kp_data.get('name', ''),
        "relationship": kp_data.get('relationship', ''),
        "contact": kp_data.get('contactInfo', ''),
        "role": kp_data.get('role', '緊急連絡先'),
        "rank": kp_data.get('rank', 1),
        "last_contact": kp_data.get('lastContact')
    })

    return {"status": "success", "data": result[0] if result else {}}


def register_family_member(fm_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """家族を登録（経済的リスクフラグ対応）"""
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        MERGE (fm:FamilyMember {name: $name, recipientName: $recipient_name})
        SET fm.relationship = $relationship,
            fm.contactStatus = $contact_status,
            fm.supportCapacity = $support_capacity,
            fm.note = $note,
            fm.riskFlag = $risk_flag,
            fm.updatedAt = datetime()
        MERGE (r)-[:HAS_FAMILY]->(fm)
        RETURN fm.name as name
    """, {
        "recipient_name": recipient_name,
        "name": fm_data.get('name', ''),
        "relationship": fm_data.get('relationship', ''),
        "contact_status": fm_data.get('contactStatus', '不明'),
        "support_capacity": fm_data.get('supportCapacity', '不明'),
        "note": fm_data.get('note', ''),
        "risk_flag": fm_data.get('riskFlag', False)
    })

    return {"status": "success", "data": result[0] if result else {}}


def register_support_organization(org_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """支援機関を登録"""
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        MERGE (so:SupportOrganization {name: $name})
        SET so.type = $type,
            so.contactPerson = $contact_person,
            so.phone = $phone,
            so.services = $services,
            so.utilizationStatus = $status,
            so.updatedAt = datetime()
        MERGE (r)-[:RECEIVES_SUPPORT_FROM]->(so)
        RETURN so.name as name
    """, {
        "recipient_name": recipient_name,
        "name": org_data.get('name', ''),
        "type": org_data.get('type', 'その他'),
        "contact_person": org_data.get('contactPerson', ''),
        "phone": org_data.get('phone', ''),
        "services": org_data.get('services', ''),
        "status": org_data.get('utilizationStatus', '利用中')
    })

    return {"status": "success", "data": result[0] if result else {}}


def register_medical_institution(med_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """医療機関を登録"""
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        MERGE (mi:MedicalInstitution {name: $name})
        SET mi.department = $department,
            mi.doctor = $doctor,
            mi.role = $role,
            mi.visitFrequency = $frequency,
            mi.updatedAt = datetime()
        MERGE (r)-[:TREATED_AT]->(mi)
        RETURN mi.name as name
    """, {
        "recipient_name": recipient_name,
        "name": med_data.get('name', ''),
        "department": med_data.get('department', ''),
        "doctor": med_data.get('doctor', ''),
        "role": med_data.get('role', 'かかりつけ'),
        "frequency": med_data.get('visitFrequency', '')
    })

    return {"status": "success", "data": result[0] if result else {}}


# =============================================================================
# 第6の柱：法的・制度的基盤
# =============================================================================

def register_protection_decision(decision_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """保護決定を登録"""
    if not decision_data.get('decisionDate'):
        return {"status": "skipped", "message": "決定情報なし"}

    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        CREATE (pd:ProtectionDecision {
            decisionDate: date($decision_date),
            type: $type,
            protectionCategory: $category,
            monthlyAmount: $amount,
            createdAt: datetime()
        })
        CREATE (r)-[:HAS_DECISION]->(pd)
        RETURN pd.type as type, pd.decisionDate as date
    """, {
        "recipient_name": recipient_name,
        "decision_date": decision_data.get('decisionDate'),
        "type": decision_data.get('type', ''),
        "category": decision_data.get('protectionCategory', ''),
        "amount": decision_data.get('monthlyAmount')
    })

    return {"status": "success", "data": result[0] if result else {}}


def register_certificate(cert_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """証明書・手帳を登録"""
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        CREATE (c:Certificate {
            type: $type,
            grade: $grade,
            expiryDate: CASE WHEN $expiry IS NOT NULL THEN date($expiry) ELSE NULL END,
            createdAt: datetime()
        })
        CREATE (r)-[:HOLDS]->(c)
        RETURN c.type as type, c.grade as grade
    """, {
        "recipient_name": recipient_name,
        "type": cert_data.get('type', ''),
        "grade": cert_data.get('grade', ''),
        "expiry": cert_data.get('expiryDate')
    })

    return {"status": "success", "data": result[0] if result else {}}


def register_support_goal(goal_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """支援目標を登録"""
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        CREATE (sg:SupportGoal {
            description: $description,
            targetDate: CASE WHEN $target_date IS NOT NULL THEN date($target_date) ELSE NULL END,
            status: $status,
            paceConsideration: $pace,
            createdAt: datetime()
        })
        CREATE (r)-[:HAS_GOAL]->(sg)
        RETURN sg.description as description
    """, {
        "recipient_name": recipient_name,
        "description": goal_data.get('description', ''),
        "target_date": goal_data.get('targetDate'),
        "status": goal_data.get('status', 'Active'),
        "pace": goal_data.get('paceConsideration', '')
    })

    return {"status": "success", "data": result[0] if result else {}}


# =============================================================================
# 第7の柱：金銭的安全と多機関連携
# =============================================================================

def register_money_management_status(mms_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """金銭管理状況を登録"""
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
        "capability": mms_data.get('capability', '不明'),
        "pattern": mms_data.get('pattern', ''),
        "risk_level": mms_data.get('riskLevel', 'Low'),
        "triggers": mms_data.get('triggers', []),
        "observations": mms_data.get('observations', ''),
        "assessment_date": mms_data.get('assessmentDate', date.today().isoformat())
    })

    if mms_data.get('riskLevel') in ['High', 'Medium']:
        log(f"金銭管理リスク登録: {recipient_name} - {mms_data.get('capability', '')}")
        create_audit_log(user_name, "CREATE", "MoneyManagementStatus",
                         f"能力: {mms_data.get('capability', '')}, リスク: {mms_data.get('riskLevel', '')}",
                         recipient_name=recipient_name)

    return {"status": "success", "data": result[0] if result else {}}


def register_economic_risk(risk_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """経済的リスクを登録（最重要）"""
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

        WITH r, er
        OPTIONAL MATCH (fm:FamilyMember {recipientName: $recipient_name})
        WHERE fm.relationship = $relationship OR fm.name = $perpetrator
        FOREACH (_ IN CASE WHEN fm IS NOT NULL THEN [1] ELSE [] END |
            MERGE (fm)-[:POSES_RISK]->(er)
            SET fm.riskFlag = true
        )

        RETURN er.type as type, er.severity as severity
    """, {
        "recipient_name": recipient_name,
        "type": risk_data.get('type', ''),
        "perpetrator": risk_data.get('perpetrator', ''),
        "relationship": risk_data.get('perpetratorRelationship', ''),
        "severity": risk_data.get('severity', 'Medium'),
        "description": risk_data.get('description', ''),
        "discovered_date": risk_data.get('discoveredDate', date.today().isoformat()),
        "status": risk_data.get('status', 'Active'),
        "interventions": risk_data.get('interventions', [])
    })

    log(f"経済的リスク登録: {recipient_name} - {risk_data.get('type', '')} (深刻度: {risk_data.get('severity', '')})")
    create_audit_log(
        user_name=user_name,
        action="CREATE",
        resource_type="EconomicRisk",
        resource_id=f"{risk_data.get('type', '')} - {risk_data.get('perpetrator', '')}",
        details=f"深刻度: {risk_data.get('severity', '')}, 状態: {risk_data.get('status', '')}",
        recipient_name=recipient_name
    )

    return {"status": "success", "data": result[0] if result else {}}


def register_daily_life_support_service(dlss_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """日常生活自立支援事業の利用を登録"""
    swc_name = dlss_data.get('socialWelfareCouncil', '')
    if swc_name:
        run_query("""
            MERGE (so:SupportOrganization {name: $name})
            SET so.type = '社会福祉協議会',
                so.updatedAt = datetime()
        """, {"name": swc_name})

    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        CREATE (dlss:DailyLifeSupportService {
            socialWelfareCouncil: $swc,
            startDate: date($start_date),
            services: $services,
            frequency: $frequency,
            specialist: $specialist,
            contactInfo: $contact,
            status: $status,
            referralRoute: $referral_route,
            reason: $reason,
            createdAt: datetime()
        })
        CREATE (r)-[:USES_SERVICE]->(dlss)

        WITH r, dlss
        OPTIONAL MATCH (so:SupportOrganization {name: $swc})
        FOREACH (_ IN CASE WHEN so IS NOT NULL THEN [1] ELSE [] END |
            MERGE (dlss)-[:PROVIDED_BY]->(so)
        )

        RETURN dlss.services as services, dlss.status as status
    """, {
        "recipient_name": recipient_name,
        "swc": swc_name,
        "start_date": dlss_data.get('startDate', date.today().isoformat()),
        "services": dlss_data.get('services', []),
        "frequency": dlss_data.get('frequency', ''),
        "specialist": dlss_data.get('specialist', ''),
        "contact": dlss_data.get('contactInfo', ''),
        "status": dlss_data.get('status', '利用中'),
        "referral_route": dlss_data.get('referralRoute', ''),
        "reason": dlss_data.get('reason', '')
    })

    log(f"日常生活自立支援事業登録: {recipient_name} - {dlss_data.get('services', [])}")
    create_audit_log(user_name, "CREATE", "DailyLifeSupportService",
                     f"サービス: {dlss_data.get('services', [])}",
                     recipient_name=recipient_name)

    return {"status": "success", "data": result[0] if result else {}}


def register_collaboration_record(collab_data: dict, recipient_name: str, user_name: str = "system") -> dict:
    """多機関連携記録を登録"""
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
            createdBy: $created_by,
            createdAt: datetime()
        })
        CREATE (cr)-[:ABOUT]->(r)

        WITH r, cr
        UNWIND $org_names as org_name
        OPTIONAL MATCH (so:SupportOrganization {name: org_name})
        FOREACH (_ IN CASE WHEN so IS NOT NULL THEN [1] ELSE [] END |
            MERGE (cr)-[:INVOLVED]->(so)
        )

        RETURN cr.date as date, cr.type as type
    """, {
        "recipient_name": recipient_name,
        "date": collab_data.get('date', date.today().isoformat()),
        "type": collab_data.get('type', 'ケース会議'),
        "participants": collab_data.get('participants', []),
        "agenda": collab_data.get('agenda', ''),
        "discussion": collab_data.get('discussion', ''),
        "decisions": collab_data.get('decisions', []),
        "next_actions": collab_data.get('nextActions', []),
        "created_by": collab_data.get('createdBy', user_name),
        "org_names": collab_data.get('involvedOrganizations', [])
    })

    log(f"連携記録登録: {recipient_name} - {collab_data.get('type', '')} ({collab_data.get('date', '')})")
    create_audit_log(user_name, "CREATE", "CollaborationRecord",
                     f"{collab_data.get('type', '')} - {collab_data.get('date', '')}",
                     recipient_name=recipient_name)

    return {"status": "success", "data": result[0] if result else {}}


def register_case_pattern(pattern_data: dict, user_name: str = "system") -> dict:
    """類似案件パターンを登録（組織知として蓄積）"""
    result = run_query("""
        MERGE (cp:CasePattern {patternName: $pattern_name})
        SET cp.description = $description,
            cp.indicators = $indicators,
            cp.riskFactors = $risk_factors,
            cp.recommendedInterventions = $interventions,
            cp.relatedServices = $related_services,
            cp.successfulCases = COALESCE(cp.successfulCases, 0) + $success_increment,
            cp.updatedAt = datetime()
        RETURN cp.patternName as patternName, cp.successfulCases as successfulCases
    """, {
        "pattern_name": pattern_data.get('patternName', ''),
        "description": pattern_data.get('description', ''),
        "indicators": pattern_data.get('indicators', []),
        "risk_factors": pattern_data.get('riskFactors', []),
        "interventions": pattern_data.get('recommendedInterventions', []),
        "related_services": pattern_data.get('relatedServices', []),
        "success_increment": pattern_data.get('successIncrement', 0)
    })

    return {"status": "success", "data": result[0] if result else {}}


def link_recipient_to_pattern(recipient_name: str, pattern_name: str, user_name: str = "system") -> dict:
    """受給者を類似案件パターンに紐付け"""
    result = run_query("""
        MATCH (r:Recipient {name: $recipient_name})
        MATCH (cp:CasePattern {patternName: $pattern_name})
        MERGE (r)-[:MATCHES_PATTERN]->(cp)
        SET cp.successfulCases = COALESCE(cp.successfulCases, 0) + 1
        RETURN r.name as recipient, cp.patternName as pattern
    """, {
        "recipient_name": recipient_name,
        "pattern_name": pattern_name
    })

    return {"status": "success", "data": result[0] if result else {}}


# =============================================================================
# 統合登録関数
# =============================================================================

def register_to_database(data: dict, user_name: str = "system") -> dict:
    """
    構造化データをNeo4jに一括登録

    Args:
        data: 構造化されたケースデータ
        user_name: 登録者名

    Returns:
        登録結果

    Raises:
        ValidationError: 入力値検証に失敗した場合
    """
    try:
        recipient_name = validate_recipient_name(data.get('recipient', {}).get('name'))
    except ValidationError as e:
        return {"status": "error", "message": str(e)}

    registered_items = []
    warnings = []

    # 1. 受給者基本情報
    if data.get('recipient'):
        register_recipient(data['recipient'], user_name)
        registered_items.append("Recipient")

    # 2. 精神疾患の状況
    if data.get('mentalHealthStatus'):
        result = register_mental_health_status(data['mentalHealthStatus'], recipient_name, user_name)
        if result['status'] == 'success':
            registered_items.append("MentalHealthStatus")
            if not data.get('ngApproaches'):
                warnings.append("精神疾患がありますが、避けるべき関わり方が登録されていません")

    # 3. 避けるべき関わり方（最重要）
    for ng in data.get('ngApproaches', []):
        if ng.get('description'):
            register_ng_approach(ng, recipient_name, user_name)
            registered_items.append("NgApproach")

    # 4. 経済的リスク
    for er in data.get('economicRisks', []):
        if er.get('type'):
            register_economic_risk(er, recipient_name, user_name)
            registered_items.append("EconomicRisk")

    # 5. 金銭管理状況
    if data.get('moneyManagementStatus'):
        register_money_management_status(data['moneyManagementStatus'], recipient_name, user_name)
        registered_items.append("MoneyManagementStatus")

    # 6. 日常生活自立支援事業
    if data.get('dailyLifeSupportService'):
        register_daily_life_support_service(data['dailyLifeSupportService'], recipient_name, user_name)
        registered_items.append("DailyLifeSupportService")

    # 7. 効果的だった関わり方
    for ea in data.get('effectiveApproaches', []):
        if ea.get('description'):
            register_effective_approach(ea, recipient_name, user_name)
            registered_items.append("EffectiveApproach")

    # 8. 注意が必要な状況
    for ts in data.get('triggerSituations', []):
        if ts.get('description'):
            register_trigger_situation(ts, recipient_name, user_name)
            registered_items.append("TriggerSituation")

    # 9. ケース記録
    for cr in data.get('caseRecords', []):
        if cr.get('content'):
            register_case_record(cr, recipient_name, user_name)
            registered_items.append("CaseRecord")

    # 10. 強み
    for s in data.get('strengths', []):
        if s.get('description'):
            register_strength(s, recipient_name, user_name)
            registered_items.append("Strength")

    # 11. 課題
    for ch in data.get('challenges', []):
        if ch.get('description'):
            register_challenge(ch, recipient_name, user_name)
            registered_items.append("Challenge")

    # 12. パターン
    for p in data.get('patterns', []):
        if p.get('description'):
            register_pattern(p, recipient_name, user_name)
            registered_items.append("Pattern")

    # 13. 申告歴
    for dh in data.get('declaredHistories', []):
        if dh.get('content'):
            register_declared_history(dh, recipient_name, user_name)
            registered_items.append("DeclaredHistory")

    # 14. 保護に至った経緯
    if data.get('pathwayToProtection'):
        register_pathway_to_protection(data['pathwayToProtection'], recipient_name, user_name)
        registered_items.append("PathwayToProtection")

    # 15. 願い
    for w in data.get('wishes', []):
        if w.get('content'):
            register_wish(w, recipient_name, user_name)
            registered_items.append("Wish")

    # 16. キーパーソン
    for kp in data.get('keyPersons', []):
        if kp.get('name'):
            register_key_person(kp, recipient_name, user_name)
            registered_items.append("KeyPerson")

    # 17. 家族
    for fm in data.get('familyMembers', []):
        if fm.get('name'):
            register_family_member(fm, recipient_name, user_name)
            registered_items.append("FamilyMember")

    # 18. 支援機関
    for so in data.get('supportOrganizations', []):
        if so.get('name'):
            register_support_organization(so, recipient_name, user_name)
            registered_items.append("SupportOrganization")

    # 19. 医療機関
    for mi in data.get('medicalInstitutions', []):
        if mi.get('name'):
            register_medical_institution(mi, recipient_name, user_name)
            registered_items.append("MedicalInstitution")

    # 20. 保護決定
    if data.get('protectionDecision'):
        register_protection_decision(data['protectionDecision'], recipient_name, user_name)
        registered_items.append("ProtectionDecision")

    # 21. 証明書
    for c in data.get('certificates', []):
        if c.get('type'):
            register_certificate(c, recipient_name, user_name)
            registered_items.append("Certificate")

    # 22. 支援目標
    for sg in data.get('supportGoals', []):
        if sg.get('description'):
            register_support_goal(sg, recipient_name, user_name)
            registered_items.append("SupportGoal")

    # 23. 連携記録
    for collab in data.get('collaborationRecords', []):
        if collab.get('type'):
            register_collaboration_record(collab, recipient_name, user_name)
            registered_items.append("CollaborationRecord")

    log(f"登録完了: {recipient_name} - 項目数: {len(registered_items)}")
    if warnings:
        for w in warnings:
            log(w, "WARN")

    return {
        "status": "success",
        "recipient_name": recipient_name,
        "registered_count": len(registered_items),
        "registered_types": list(set(registered_items)),
        "warnings": warnings
    }
