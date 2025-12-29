"""
生活保護受給者尊厳支援データベース - 監査ログモジュール
Manifesto: Livelihood Protection Support & Dignity Graph 準拠

セキュリティ基準: TECHNICAL_STANDARDS.md 4.4準拠
- 全操作の監査ログ記録
- ハッシュチェーンによる改ざん防止（FR-006-02）
- 追記専用（削除禁止）
"""

import uuid
import hashlib
import json
from datetime import datetime
from typing import Optional

from .db_connection import run_query, run_query_single, log
from .validation import validate_enum, validate_string, validate_date_string


# 監査ログで許可されるアクション
AUDIT_ACTIONS = ["CREATE", "READ", "UPDATE", "DELETE", "LOGIN", "LOGOUT", "EXPORT"]

# ハッシュチェーンの初期値（ジェネシスブロック）
GENESIS_HASH = "0" * 64


# =============================================================================
# ハッシュチェーン関連関数
# =============================================================================

def _compute_log_hash(
    timestamp: str,
    user_name: str,
    action: str,
    resource_type: str,
    resource_id: str,
    previous_hash: str,
    details: str = ""
) -> str:
    """
    監査ログエントリのSHA-256ハッシュを計算

    Args:
        timestamp: タイムスタンプ（ISO形式）
        user_name: ユーザー名
        action: アクション種別
        resource_type: リソース種別
        resource_id: リソースID
        previous_hash: 前のログエントリのハッシュ
        details: 詳細情報

    Returns:
        SHA-256ハッシュ値（64文字の16進数文字列）
    """
    # ハッシュ対象のデータを正規化
    data = {
        "timestamp": timestamp,
        "user_name": user_name,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "previous_hash": previous_hash,
        "details": details
    }

    # JSON形式で正規化（キーをソート）
    normalized = json.dumps(data, sort_keys=True, ensure_ascii=False)

    # SHA-256ハッシュを計算
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def _get_previous_hash() -> str:
    """
    直前の監査ログエントリのハッシュを取得

    Returns:
        前のエントリのハッシュ値、存在しない場合はGENESIS_HASH
    """
    result = run_query_single("""
        MATCH (al:AuditLog)
        WHERE al.entryHash IS NOT NULL
        RETURN al.entryHash as hash
        ORDER BY al.timestamp DESC, al.sequenceNumber DESC
        LIMIT 1
    """)

    if result and result.get('hash'):
        return result['hash']
    return GENESIS_HASH


def _get_next_sequence_number() -> int:
    """
    次のシーケンス番号を取得

    Returns:
        次のシーケンス番号
    """
    result = run_query_single("""
        MATCH (al:AuditLog)
        RETURN max(al.sequenceNumber) as max_seq
    """)

    if result and result.get('max_seq') is not None:
        return result['max_seq'] + 1
    return 1


# =============================================================================
# 監査ログ作成
# =============================================================================

def create_audit_log(
    user_name: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: str = "",
    recipient_name: str = None,
    ip_address: str = None,
    user_agent: str = None,
    session_id: str = None,
    result_status: str = "SUCCESS"
) -> dict:
    """
    監査ログを作成（TECHNICAL_STANDARDS.md 4.4準拠 + ハッシュチェーン）

    ハッシュチェーンにより、過去のログエントリの改ざんを検出可能。
    各エントリは前のエントリのハッシュを含み、連続性を保証する。

    Args:
        user_name: 操作ユーザー名
        action: 操作種別（CREATE/READ/UPDATE/DELETE/LOGIN/LOGOUT/EXPORT）
        resource_type: 対象リソース種別
        resource_id: 対象リソースID/名前
        details: 追加詳細情報
        recipient_name: 関連する受給者名（オプション）
        ip_address: クライアントIPアドレス（オプション）
        user_agent: ブラウザ/クライアント情報（オプション）
        session_id: セッションID（オプション）
        result_status: 結果（SUCCESS/FAILURE）

    Returns:
        作成された監査ログ情報（ハッシュ値含む）
    """
    # アクションの検証
    validated_action = validate_enum(action, "action", AUDIT_ACTIONS, required=True)

    # 結果ステータスの検証
    validated_result = validate_enum(
        result_status, "result_status", ["SUCCESS", "FAILURE"], required=True
    )

    # ユーザー名の検証
    validated_user = validate_string(user_name, "user_name", required=True, max_length=100)

    # タイムスタンプとID生成
    timestamp = datetime.utcnow().isoformat() + "Z"
    request_id = f"req_{uuid.uuid4().hex[:12]}"

    # ハッシュチェーン: 前のエントリのハッシュを取得
    previous_hash = _get_previous_hash()
    sequence_number = _get_next_sequence_number()

    # このエントリのハッシュを計算
    entry_hash = _compute_log_hash(
        timestamp=timestamp,
        user_name=validated_user,
        action=validated_action,
        resource_type=resource_type,
        resource_id=resource_id,
        previous_hash=previous_hash,
        details=details
    )

    result = run_query("""
        CREATE (al:AuditLog {
            timestamp: datetime($timestamp),
            level: 'INFO',
            eventType: 'AUDIT',
            userId: $user_name,
            username: $user_name,
            action: $action,
            resourceType: $resource_type,
            resourceId: $resource_id,
            clientId: $recipient_name,
            ipAddress: $ip_address,
            userAgent: $user_agent,
            result: $result_status,
            sessionId: $session_id,
            requestId: $request_id,
            details: $details,
            sequenceNumber: $sequence_number,
            previousHash: $previous_hash,
            entryHash: $entry_hash
        })
        RETURN al.timestamp as timestamp,
               al.action as action,
               al.requestId as requestId,
               al.sequenceNumber as sequenceNumber,
               al.entryHash as entryHash
    """, {
        "timestamp": timestamp,
        "user_name": validated_user,
        "action": validated_action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details,
        "recipient_name": recipient_name or "",
        "ip_address": ip_address or "unknown",
        "user_agent": user_agent or "unknown",
        "session_id": session_id or "",
        "result_status": validated_result,
        "request_id": request_id,
        "sequence_number": sequence_number,
        "previous_hash": previous_hash,
        "entry_hash": entry_hash
    })

    log(f"監査ログ: {validated_user} - {validated_action} - {resource_type}:{resource_id} [{validated_result}] (seq:{sequence_number})")
    return result[0] if result else {}


# =============================================================================
# 監査ログ検索
# =============================================================================

def get_audit_logs(
    user_name: str = None,
    action: str = None,
    resource_type: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 100
) -> list:
    """
    監査ログの検索

    Args:
        user_name: フィルタ - ユーザー名
        action: フィルタ - アクション種別
        resource_type: フィルタ - リソース種別
        start_date: フィルタ - 開始日（YYYY-MM-DD）
        end_date: フィルタ - 終了日（YYYY-MM-DD）
        limit: 取得件数上限

    Returns:
        監査ログのリスト
    """
    # 日付の検証
    if start_date:
        validate_date_string(start_date, "start_date")
    if end_date:
        validate_date_string(end_date, "end_date")

    query = """
        MATCH (al:AuditLog)
        WHERE ($user_name IS NULL OR al.username = $user_name)
          AND ($action IS NULL OR al.action = $action)
          AND ($resource_type IS NULL OR al.resourceType = $resource_type)
          AND ($start_date IS NULL OR al.timestamp >= datetime($start_date))
          AND ($end_date IS NULL OR al.timestamp <= datetime($end_date + 'T23:59:59'))
        RETURN al.timestamp as timestamp,
               al.username as username,
               al.action as action,
               al.resourceType as resourceType,
               al.resourceId as resourceId,
               al.clientId as clientId,
               al.result as result,
               al.details as details,
               al.requestId as requestId,
               al.sequenceNumber as sequenceNumber,
               al.entryHash as entryHash
        ORDER BY al.timestamp DESC
        LIMIT $limit
    """

    return run_query(query, {
        "user_name": user_name,
        "action": action,
        "resource_type": resource_type,
        "start_date": start_date,
        "end_date": end_date,
        "limit": limit
    })


# =============================================================================
# ハッシュチェーン検証
# =============================================================================

def verify_chain_integrity(start_seq: int = 1, end_seq: int = None) -> dict:
    """
    監査ログのハッシュチェーン整合性を検証

    Args:
        start_seq: 検証開始シーケンス番号（デフォルト: 1）
        end_seq: 検証終了シーケンス番号（デフォルト: 最新まで）

    Returns:
        検証結果:
        - is_valid: 整合性が保たれているか
        - total_entries: 検証したエントリ数
        - first_invalid_seq: 最初に不整合が見つかったシーケンス番号（あれば）
        - errors: エラー詳細のリスト
    """
    # 検証対象のログを取得
    query = """
        MATCH (al:AuditLog)
        WHERE al.sequenceNumber >= $start_seq
        """ + ("AND al.sequenceNumber <= $end_seq" if end_seq else "") + """
        RETURN al.timestamp as timestamp,
               al.username as username,
               al.action as action,
               al.resourceType as resourceType,
               al.resourceId as resourceId,
               al.details as details,
               al.sequenceNumber as sequenceNumber,
               al.previousHash as previousHash,
               al.entryHash as entryHash
        ORDER BY al.sequenceNumber ASC
    """

    logs = run_query(query, {"start_seq": start_seq, "end_seq": end_seq})

    if not logs:
        return {
            "is_valid": True,
            "total_entries": 0,
            "first_invalid_seq": None,
            "errors": []
        }

    errors = []
    expected_previous_hash = GENESIS_HASH if start_seq == 1 else None

    # start_seq > 1 の場合、直前のエントリのハッシュを取得
    if start_seq > 1:
        prev_log = run_query_single("""
            MATCH (al:AuditLog)
            WHERE al.sequenceNumber = $prev_seq
            RETURN al.entryHash as entryHash
        """, {"prev_seq": start_seq - 1})

        if prev_log:
            expected_previous_hash = prev_log.get('entryHash')
        else:
            errors.append(f"シーケンス {start_seq - 1} のログが見つかりません")

    for entry in logs:
        seq = entry['sequenceNumber']

        # 1. 前のハッシュとの連続性を確認
        if expected_previous_hash is not None:
            if entry['previousHash'] != expected_previous_hash:
                errors.append(
                    f"シーケンス {seq}: previousHashの不一致 "
                    f"(expected: {expected_previous_hash[:16]}..., "
                    f"actual: {entry['previousHash'][:16] if entry['previousHash'] else 'None'}...)"
                )

        # 2. エントリ自体のハッシュを再計算して検証
        timestamp_str = entry['timestamp'].isoformat() if hasattr(entry['timestamp'], 'isoformat') else str(entry['timestamp'])

        computed_hash = _compute_log_hash(
            timestamp=timestamp_str,
            user_name=entry['username'],
            action=entry['action'],
            resource_type=entry['resourceType'],
            resource_id=entry['resourceId'],
            previous_hash=entry['previousHash'] or GENESIS_HASH,
            details=entry['details'] or ""
        )

        if computed_hash != entry['entryHash']:
            errors.append(
                f"シーケンス {seq}: entryHashの不一致 "
                f"(computed: {computed_hash[:16]}..., "
                f"stored: {entry['entryHash'][:16] if entry['entryHash'] else 'None'}...)"
            )

        # 次のエントリの検証用に現在のハッシュを保持
        expected_previous_hash = entry['entryHash']

    first_invalid = None
    if errors:
        # エラーメッセージからシーケンス番号を抽出
        import re
        for error in errors:
            match = re.search(r'シーケンス (\d+)', error)
            if match:
                first_invalid = int(match.group(1))
                break

    return {
        "is_valid": len(errors) == 0,
        "total_entries": len(logs),
        "first_invalid_seq": first_invalid,
        "errors": errors
    }


def get_chain_status() -> dict:
    """
    ハッシュチェーンの現在のステータスを取得

    Returns:
        チェーンのステータス情報
    """
    stats = run_query_single("""
        MATCH (al:AuditLog)
        RETURN count(al) as total_entries,
               max(al.sequenceNumber) as latest_sequence,
               min(al.sequenceNumber) as first_sequence
    """)

    latest = run_query_single("""
        MATCH (al:AuditLog)
        WHERE al.sequenceNumber IS NOT NULL
        RETURN al.timestamp as timestamp,
               al.sequenceNumber as sequenceNumber,
               al.entryHash as entryHash
        ORDER BY al.sequenceNumber DESC
        LIMIT 1
    """)

    return {
        "total_entries": stats['total_entries'] if stats else 0,
        "first_sequence": stats['first_sequence'] if stats else None,
        "latest_sequence": stats['latest_sequence'] if stats else None,
        "latest_hash": latest['entryHash'] if latest else None,
        "latest_timestamp": latest['timestamp'] if latest else None,
        "genesis_hash": GENESIS_HASH
    }
