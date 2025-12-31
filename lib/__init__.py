"""
生活保護受給者尊厳支援データベース - ライブラリパッケージ
Manifesto: Livelihood Protection Support & Dignity Graph 準拠

モジュール構成:
- db_connection: Neo4j接続管理
- db_queries: データ取得・検索
- db_operations: CRUD操作
- validation: 入力値検証
- audit: 監査ログ
- ai_extractor: AI構造化抽出
- utils: ユーティリティ
- file_readers: ファイル読み込み
"""

# DB接続
from .db_connection import run_query, run_query_single, get_driver, close_driver

# 入力値検証
from .validation import (
    ValidationError,
    validate_string,
    validate_date_string,
    validate_enum,
    sanitize_for_neo4j,
    validate_recipient_name,
)

# 監査ログ（ハッシュチェーン対応）
from .audit import (
    create_audit_log,
    get_audit_logs,
    verify_chain_integrity,
    get_chain_status,
    GENESIS_HASH,
)

# データ取得・検索
from .db_queries import (
    get_recipients_list,
    get_recipient_stats,
    get_recipient_profile,
    get_handover_summary,
    search_similar_cases,
    find_matching_patterns,
    get_visit_briefing,
    get_collaboration_history,
)

# CRUD操作
from .db_operations import register_to_database

# AI抽出
from .ai_extractor import extract_from_text, detect_critical_expressions, validate_extracted_data

# ユーティリティ
from .utils import (
    safe_date_parse,
    calculate_age,
    format_date_with_age,
    init_session_state,
    reset_session_state,
    get_input_example,
    get_risk_emoji,
    format_mental_health_warning,
)

# ファイル読み込み
from .file_readers import read_uploaded_file, get_supported_extensions, check_dependencies

# 認証（Keycloak OIDC）
from .auth import (
    init_auth_session,
    is_authenticated,
    get_current_user,
    has_role,
    require_role,
    require_authentication,
    render_login_button,
    render_user_info,
    logout,
)

__all__ = [
    # DB接続
    'run_query',
    'run_query_single',
    'get_driver',
    'close_driver',
    # 入力値検証
    'ValidationError',
    'validate_string',
    'validate_date_string',
    'validate_enum',
    'sanitize_for_neo4j',
    'validate_recipient_name',
    # 監査ログ（ハッシュチェーン対応）
    'create_audit_log',
    'get_audit_logs',
    'verify_chain_integrity',
    'get_chain_status',
    'GENESIS_HASH',
    # データ取得・検索
    'get_recipients_list',
    'get_recipient_stats',
    'get_recipient_profile',
    'get_handover_summary',
    'search_similar_cases',
    'find_matching_patterns',
    'get_visit_briefing',
    'get_collaboration_history',
    # CRUD操作
    'register_to_database',
    # AI抽出
    'extract_from_text',
    'detect_critical_expressions',
    'validate_extracted_data',
    # ユーティリティ
    'safe_date_parse',
    'calculate_age',
    'format_date_with_age',
    'init_session_state',
    'reset_session_state',
    'get_input_example',
    'get_risk_emoji',
    'format_mental_health_warning',
    # ファイル読み込み
    'read_uploaded_file',
    'get_supported_extensions',
    'check_dependencies',
    # 認証（Keycloak OIDC）
    'init_auth_session',
    'is_authenticated',
    'get_current_user',
    'has_role',
    'require_role',
    'require_authentication',
    'render_login_button',
    'render_user_info',
    'logout',
]
