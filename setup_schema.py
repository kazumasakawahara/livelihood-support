"""
生活保護受給者尊厳支援データベース - 初期スキーマ設定
Manifesto: Livelihood Protection Support & Dignity Graph 準拠（Version 1.4）

インデックスと制約の作成、類似案件パターンの初期データ登録
"""

import os
import sys
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

# Neo4j接続
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)


def run_query(query: str, params: dict = None):
    """Cypherクエリ実行"""
    with driver.session() as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]


def log(message: str, level: str = "INFO"):
    """ログ出力"""
    emoji = {"INFO": "ℹ️", "SUCCESS": "✅", "WARN": "⚠️", "ERROR": "❌"}.get(level, "")
    print(f"{emoji} [{level}] {message}")


def setup_constraints():
    """一意性制約の作成"""
    log("制約を設定中...")
    
    constraints = [
        # 受給者名は一意
        ("Recipient", "name", "recipient_name_unique"),
        # ケースパターン名は一意
        ("CasePattern", "patternName", "case_pattern_name_unique"),
    ]
    
    for label, property, name in constraints:
        try:
            run_query(f"""
                CREATE CONSTRAINT {name} IF NOT EXISTS
                FOR (n:{label})
                REQUIRE n.{property} IS UNIQUE
            """)
            log(f"  制約作成: {name}", "SUCCESS")
        except Exception as e:
            log(f"  制約作成スキップ（既存）: {name}", "WARN")


def setup_indexes():
    """インデックスの作成"""
    log("インデックスを設定中...")
    
    indexes = [
        # 第1の柱：ケース記録
        ("CaseRecord", "date", "case_record_date_idx"),
        ("CaseRecord", "category", "case_record_category_idx"),
        ("HomeVisit", "date", "home_visit_date_idx"),
        
        # 第2の柱：抽出された本人像
        ("MentalHealthStatus", "diagnosis", "mental_health_diagnosis_idx"),
        
        # 第3の柱：関わり方の知恵
        ("NgApproach", "riskLevel", "ng_approach_risk_idx"),
        ("EffectiveApproach", "description", "effective_approach_desc_idx"),
        
        # 第4の柱：申告歴
        ("DeclaredHistory", "era", "declared_history_era_idx"),
        
        # 第5の柱：社会的ネットワーク
        ("KeyPerson", "name", "key_person_name_idx"),
        ("FamilyMember", "recipientName", "family_member_recipient_idx"),
        ("SupportOrganization", "name", "support_org_name_idx"),
        ("SupportOrganization", "type", "support_org_type_idx"),
        
        # 第6の柱：法的基盤
        ("Certificate", "type", "certificate_type_idx"),
        ("Certificate", "expiryDate", "certificate_expiry_idx"),
        
        # 第7の柱：金銭的安全と多機関連携
        ("MoneyManagementStatus", "recipientName", "money_status_recipient_idx"),
        ("MoneyManagementStatus", "capability", "money_status_capability_idx"),
        ("EconomicRisk", "type", "economic_risk_type_idx"),
        ("EconomicRisk", "severity", "economic_risk_severity_idx"),
        ("EconomicRisk", "status", "economic_risk_status_idx"),
        ("DailyLifeSupportService", "status", "daily_life_support_status_idx"),
        ("CollaborationRecord", "date", "collaboration_date_idx"),
        ("CollaborationRecord", "type", "collaboration_type_idx"),
        
        # 監査ログ
        ("AuditLog", "timestamp", "audit_log_timestamp_idx"),
        ("AuditLog", "user", "audit_log_user_idx"),
    ]
    
    for label, property, name in indexes:
        try:
            run_query(f"""
                CREATE INDEX {name} IF NOT EXISTS
                FOR (n:{label})
                ON (n.{property})
            """)
            log(f"  インデックス作成: {name}", "SUCCESS")
        except Exception as e:
            log(f"  インデックス作成スキップ（既存）: {name}", "WARN")


def register_case_patterns():
    """類似案件パターンの初期データを登録（組織知として蓄積）"""
    log("類似案件パターンを登録中...")
    
    patterns = [
        {
            "patternName": "親族による金銭搾取（同居家族）",
            "description": "同居する親族（主に子や兄弟）が保護費を搾取するパターン。本人は断れない心理状態にあることが多い。",
            "indicators": [
                "受給日直後に金銭がなくなる",
                "特定の親族との接触後に困窮",
                "本人が搾取を認めない/擁護する",
                "親族への恐怖心がある"
            ],
            "riskFactors": [
                "判断能力の低下",
                "親族への依存",
                "孤立",
                "DV歴",
                "精神疾患"
            ],
            "recommendedInterventions": [
                "日常生活自立支援事業の導入",
                "本人との信頼関係構築を優先",
                "親族との接触機会の調整（訪問日の変更等）",
                "地域包括支援センターとの連携",
                "必要に応じて成年後見制度の検討"
            ],
            "relatedServices": [
                "日常生活自立支援事業",
                "成年後見制度",
                "地域包括支援センター"
            ],
            "successfulCases": 0
        },
        {
            "patternName": "親族による金銭搾取（別居家族）",
            "description": "別居する親族が定期的に訪問し、金銭を要求・搾取するパターン。訪問頻度と金銭枯渇のタイミングに相関がある。",
            "indicators": [
                "特定の親族の訪問後に困窮",
                "訪問頻度が保護費支給日に集中",
                "「仕方ない」「家族だから」という発言",
                "訪問を嫌がる様子"
            ],
            "riskFactors": [
                "親族への情緒的依存",
                "過去のDV/虐待関係",
                "断る力の欠如",
                "認知機能の低下"
            ],
            "recommendedInterventions": [
                "日常生活自立支援事業の導入",
                "訪問日・時間の調整（保護費支給日を避ける）",
                "本人が断れるようエンパワメント",
                "必要に応じて警察への相談"
            ],
            "relatedServices": [
                "日常生活自立支援事業",
                "DV相談窓口",
                "警察"
            ],
            "successfulCases": 0
        },
        {
            "patternName": "認知機能低下による金銭管理困難",
            "description": "認知症や知的障害により計画的な金銭管理ができないパターン。悪意のある搾取ではなく、本人の能力の問題。",
            "indicators": [
                "計画的にお金を使えない",
                "同じものを何度も購入",
                "詐欺被害に遭いやすい",
                "公共料金の滞納が繰り返される"
            ],
            "riskFactors": [
                "認知症",
                "知的障害",
                "精神疾患",
                "高齢"
            ],
            "recommendedInterventions": [
                "日常生活自立支援事業の導入",
                "定期的な見守り訪問",
                "認知症の場合は成年後見制度の検討",
                "地域包括支援センターとの連携"
            ],
            "relatedServices": [
                "日常生活自立支援事業",
                "成年後見制度",
                "地域包括支援センター",
                "認知症疾患医療センター"
            ],
            "successfulCases": 0
        },
        {
            "patternName": "ギャンブル依存による浪費",
            "description": "ギャンブル依存により保護費を短期間で使い果たすパターン。本人の意志だけでは改善が難しい。",
            "indicators": [
                "受給日から数日で金銭がなくなる",
                "パチンコ・競馬等への言及",
                "「今度こそ」「取り返す」という発言",
                "借金がある"
            ],
            "riskFactors": [
                "ギャンブル依存症",
                "ストレスへの脆弱性",
                "孤立",
                "過去の成功体験"
            ],
            "recommendedInterventions": [
                "依存症専門外来への受診勧奨",
                "日常生活自立支援事業の導入",
                "自助グループ（GA等）への参加支援",
                "分割支給の検討"
            ],
            "relatedServices": [
                "依存症専門外来",
                "日常生活自立支援事業",
                "ギャンブラーズ・アノニマス（GA）",
                "精神保健福祉センター"
            ],
            "successfulCases": 0
        },
        {
            "patternName": "詐欺被害リスク（高齢者）",
            "description": "高齢で判断力が低下し、電話詐欺や訪問販売詐欺の被害に遭いやすいパターン。",
            "indicators": [
                "不審な電話・訪問への言及",
                "「お金を送った」「振り込んだ」という発言",
                "見知らぬ人からの連絡",
                "高額な商品の購入"
            ],
            "riskFactors": [
                "高齢",
                "独居",
                "認知機能の低下",
                "孤立",
                "お人好し"
            ],
            "recommendedInterventions": [
                "日常生活自立支援事業の導入",
                "通帳・印鑑の預かりサービス",
                "地域の見守りネットワークへの登録",
                "消費生活センターへの相談"
            ],
            "relatedServices": [
                "日常生活自立支援事業",
                "消費生活センター",
                "地域見守りネットワーク",
                "警察（特殊詐欺対策）"
            ],
            "successfulCases": 0
        },
        {
            "patternName": "精神疾患による就労圧力への脆弱性",
            "description": "精神疾患があるにもかかわらず就労指導を受け、症状が悪化するパターン。支援者による二次被害の典型例。",
            "indicators": [
                "就労指導後の症状悪化",
                "「働けない自分はダメだ」という発言",
                "ケースワーカーへの恐怖・回避",
                "面談後の体調不良"
            ],
            "riskFactors": [
                "うつ病",
                "不安障害",
                "統合失調症",
                "自己肯定感の低さ"
            ],
            "recommendedInterventions": [
                "就労指導の一時停止を主治医と協議",
                "本人のペースを尊重",
                "小さな成功体験を積む支援",
                "批判的指導を絶対に避ける"
            ],
            "relatedServices": [
                "精神科医療機関",
                "就労継続支援B型",
                "地域活動支援センター"
            ],
            "successfulCases": 0
        },
    ]
    
    for pattern in patterns:
        try:
            run_query("""
                MERGE (cp:CasePattern {patternName: $patternName})
                SET cp.description = $description,
                    cp.indicators = $indicators,
                    cp.riskFactors = $riskFactors,
                    cp.recommendedInterventions = $recommendedInterventions,
                    cp.relatedServices = $relatedServices,
                    cp.successfulCases = $successfulCases,
                    cp.createdAt = datetime()
            """, pattern)
            log(f"  パターン登録: {pattern['patternName']}", "SUCCESS")
        except Exception as e:
            log(f"  パターン登録失敗: {pattern['patternName']} - {e}", "ERROR")


def verify_setup():
    """設定確認"""
    log("設定を確認中...")
    
    # ノード数の確認
    stats = run_query("""
        CALL apoc.meta.stats() YIELD labels
        RETURN labels
    """)
    
    if stats:
        labels = stats[0].get('labels', {})
        log("ノード数:")
        for label, count in labels.items():
            if count > 0:
                log(f"  {label}: {count}")
    
    # パターン数の確認
    pattern_count = run_query("MATCH (cp:CasePattern) RETURN count(cp) as c")[0]['c']
    log(f"類似案件パターン: {pattern_count}件", "SUCCESS")


def main():
    """メイン処理"""
    print("=" * 60)
    print("生活保護受給者尊厳支援データベース - 初期設定")
    print("Manifesto Version 1.4 準拠")
    print("=" * 60)
    print()
    
    try:
        setup_constraints()
        print()
        
        setup_indexes()
        print()
        
        register_case_patterns()
        print()
        
        verify_setup()
        print()
        
        print("=" * 60)
        log("初期設定が完了しました", "SUCCESS")
        print("=" * 60)
        
    except Exception as e:
        log(f"初期設定でエラーが発生しました: {e}", "ERROR")
        sys.exit(1)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
