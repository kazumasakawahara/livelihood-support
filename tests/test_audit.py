"""
lib/audit.py のユニットテスト
監査ログのハッシュチェーン機能のテスト
"""

import pytest
import hashlib
import json
from lib.audit import (
    _compute_log_hash,
    GENESIS_HASH,
    AUDIT_ACTIONS,
)


class TestComputeLogHash:
    """_compute_log_hash関数のテスト"""

    def test_hash_format(self):
        """ハッシュ値の形式確認（64文字の16進数）"""
        result = _compute_log_hash(
            timestamp="2024-12-28T10:00:00Z",
            user_name="test_user",
            action="CREATE",
            resource_type="CaseRecord",
            resource_id="123",
            previous_hash=GENESIS_HASH,
            details=""
        )
        assert len(result) == 64
        assert all(c in '0123456789abcdef' for c in result)

    def test_deterministic_hash(self):
        """同じ入力で同じハッシュが生成される"""
        params = {
            "timestamp": "2024-12-28T10:00:00Z",
            "user_name": "test_user",
            "action": "CREATE",
            "resource_type": "CaseRecord",
            "resource_id": "123",
            "previous_hash": GENESIS_HASH,
            "details": "テスト詳細"
        }
        result1 = _compute_log_hash(**params)
        result2 = _compute_log_hash(**params)
        assert result1 == result2

    def test_different_input_different_hash(self):
        """異なる入力で異なるハッシュが生成される"""
        base_params = {
            "timestamp": "2024-12-28T10:00:00Z",
            "user_name": "test_user",
            "action": "CREATE",
            "resource_type": "CaseRecord",
            "resource_id": "123",
            "previous_hash": GENESIS_HASH,
            "details": ""
        }

        result1 = _compute_log_hash(**base_params)

        # タイムスタンプを変更
        modified = base_params.copy()
        modified["timestamp"] = "2024-12-28T10:00:01Z"
        result2 = _compute_log_hash(**modified)

        assert result1 != result2

    def test_user_change_affects_hash(self):
        """ユーザー名の変更でハッシュが変わる"""
        params = {
            "timestamp": "2024-12-28T10:00:00Z",
            "user_name": "user1",
            "action": "CREATE",
            "resource_type": "CaseRecord",
            "resource_id": "123",
            "previous_hash": GENESIS_HASH,
            "details": ""
        }
        result1 = _compute_log_hash(**params)

        params["user_name"] = "user2"
        result2 = _compute_log_hash(**params)

        assert result1 != result2

    def test_previous_hash_affects_hash(self):
        """前のハッシュの変更でハッシュが変わる（チェーン検証の基盤）"""
        params = {
            "timestamp": "2024-12-28T10:00:00Z",
            "user_name": "test_user",
            "action": "CREATE",
            "resource_type": "CaseRecord",
            "resource_id": "123",
            "previous_hash": GENESIS_HASH,
            "details": ""
        }
        result1 = _compute_log_hash(**params)

        params["previous_hash"] = "a" * 64
        result2 = _compute_log_hash(**params)

        assert result1 != result2

    def test_details_affects_hash(self):
        """詳細の変更でハッシュが変わる"""
        params = {
            "timestamp": "2024-12-28T10:00:00Z",
            "user_name": "test_user",
            "action": "CREATE",
            "resource_type": "CaseRecord",
            "resource_id": "123",
            "previous_hash": GENESIS_HASH,
            "details": "詳細1"
        }
        result1 = _compute_log_hash(**params)

        params["details"] = "詳細2"
        result2 = _compute_log_hash(**params)

        assert result1 != result2

    def test_japanese_characters(self):
        """日本語文字列のハッシュ計算"""
        result = _compute_log_hash(
            timestamp="2024-12-28T10:00:00Z",
            user_name="鈴木ケースワーカー",
            action="CREATE",
            resource_type="ケース記録",
            resource_id="山田太郎",
            previous_hash=GENESIS_HASH,
            details="訪問記録を作成しました"
        )
        assert len(result) == 64


class TestGenesisHash:
    """ジェネシスハッシュのテスト"""

    def test_genesis_hash_format(self):
        """ジェネシスハッシュは64個のゼロ"""
        assert len(GENESIS_HASH) == 64
        assert GENESIS_HASH == "0" * 64


class TestAuditActions:
    """監査アクションのテスト"""

    def test_required_actions(self):
        """必須アクションが定義されている"""
        required = ["CREATE", "READ", "UPDATE", "DELETE", "LOGIN", "LOGOUT", "EXPORT"]
        for action in required:
            assert action in AUDIT_ACTIONS

    def test_action_count(self):
        """アクション数の確認"""
        assert len(AUDIT_ACTIONS) == 7


class TestHashChainIntegrity:
    """ハッシュチェーンの整合性テスト"""

    def test_chain_construction(self):
        """チェーンの構築と検証"""
        entries = []

        # エントリ1（ジェネシス）
        hash1 = _compute_log_hash(
            timestamp="2024-12-28T10:00:00Z",
            user_name="user1",
            action="CREATE",
            resource_type="Test",
            resource_id="1",
            previous_hash=GENESIS_HASH,
            details=""
        )
        entries.append({
            "previous_hash": GENESIS_HASH,
            "entry_hash": hash1
        })

        # エントリ2（エントリ1にリンク）
        hash2 = _compute_log_hash(
            timestamp="2024-12-28T10:01:00Z",
            user_name="user2",
            action="UPDATE",
            resource_type="Test",
            resource_id="1",
            previous_hash=hash1,
            details=""
        )
        entries.append({
            "previous_hash": hash1,
            "entry_hash": hash2
        })

        # エントリ3（エントリ2にリンク）
        hash3 = _compute_log_hash(
            timestamp="2024-12-28T10:02:00Z",
            user_name="user1",
            action="READ",
            resource_type="Test",
            resource_id="1",
            previous_hash=hash2,
            details=""
        )
        entries.append({
            "previous_hash": hash2,
            "entry_hash": hash3
        })

        # チェーンの検証
        assert entries[0]["previous_hash"] == GENESIS_HASH
        assert entries[1]["previous_hash"] == entries[0]["entry_hash"]
        assert entries[2]["previous_hash"] == entries[1]["entry_hash"]

    def test_tamper_detection(self):
        """改ざん検出のテスト"""
        # 元のエントリ
        original_hash = _compute_log_hash(
            timestamp="2024-12-28T10:00:00Z",
            user_name="honest_user",
            action="CREATE",
            resource_type="Test",
            resource_id="1",
            previous_hash=GENESIS_HASH,
            details="正当な操作"
        )

        # 改ざんされたエントリ（ユーザー名を変更）
        tampered_hash = _compute_log_hash(
            timestamp="2024-12-28T10:00:00Z",
            user_name="attacker",  # 改ざん
            action="CREATE",
            resource_type="Test",
            resource_id="1",
            previous_hash=GENESIS_HASH,
            details="正当な操作"
        )

        # ハッシュが異なることで改ざんを検出
        assert original_hash != tampered_hash

    def test_chain_break_detection(self):
        """チェーン切断の検出テスト"""
        # 正常なチェーン
        hash1 = _compute_log_hash(
            timestamp="2024-12-28T10:00:00Z",
            user_name="user1",
            action="CREATE",
            resource_type="Test",
            resource_id="1",
            previous_hash=GENESIS_HASH,
            details=""
        )

        # 正しい次のエントリ
        correct_hash2 = _compute_log_hash(
            timestamp="2024-12-28T10:01:00Z",
            user_name="user2",
            action="UPDATE",
            resource_type="Test",
            resource_id="1",
            previous_hash=hash1,  # 正しいリンク
            details=""
        )

        # 不正な次のエントリ（間違ったprevious_hash）
        wrong_hash2 = _compute_log_hash(
            timestamp="2024-12-28T10:01:00Z",
            user_name="user2",
            action="UPDATE",
            resource_type="Test",
            resource_id="1",
            previous_hash=GENESIS_HASH,  # 不正なリンク
            details=""
        )

        # ハッシュが異なることでチェーン切断を検出
        assert correct_hash2 != wrong_hash2
