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


class TestCreateAuditLogValidation:
    """create_audit_log関数のバリデーションテスト"""

    @pytest.fixture
    def mock_db(self):
        """データベース関連のモック"""
        from unittest.mock import patch
        with patch('lib.audit.run_query') as mock_query, \
             patch('lib.audit.run_query_single') as mock_single:
            mock_single.return_value = {'hash': 'a' * 64, 'max_seq': 1}
            mock_query.return_value = [{'timestamp': '2024-01-01', 'action': 'CREATE'}]
            yield mock_query, mock_single

    def test_invalid_action_raises_error(self, mock_db):
        """無効なアクションでエラー発生"""
        from lib.audit import create_audit_log
        from lib.validation import ValidationError

        with pytest.raises(ValidationError):
            create_audit_log(
                user_name="test_user",
                action="INVALID",
                resource_type="Test",
                resource_id="123"
            )

    def test_none_user_raises_error(self, mock_db):
        """Noneのユーザー名でエラー発生"""
        from lib.audit import create_audit_log
        from lib.validation import ValidationError

        with pytest.raises(ValidationError):
            create_audit_log(
                user_name=None,
                action="CREATE",
                resource_type="Test",
                resource_id="123"
            )

    def test_invalid_result_status_raises_error(self, mock_db):
        """無効な結果ステータスでエラー発生"""
        from lib.audit import create_audit_log
        from lib.validation import ValidationError

        with pytest.raises(ValidationError):
            create_audit_log(
                user_name="test_user",
                action="CREATE",
                resource_type="Test",
                resource_id="123",
                result_status="INVALID"
            )

    def test_valid_crud_actions(self, mock_db):
        """有効なCRUDアクションでエラーなし"""
        from lib.audit import create_audit_log

        for action in ["CREATE", "READ", "UPDATE", "DELETE"]:
            # 例外が発生しないことを確認
            result = create_audit_log(
                user_name="test_user",
                action=action,
                resource_type="Test",
                resource_id="123"
            )
            assert result is not None

    def test_valid_auth_actions(self, mock_db):
        """有効な認証アクションでエラーなし"""
        from lib.audit import create_audit_log

        for action in ["LOGIN", "LOGOUT"]:
            result = create_audit_log(
                user_name="test_user",
                action=action,
                resource_type="Session",
                resource_id="session123"
            )
            assert result is not None


class TestGetAuditLogsValidation:
    """get_audit_logs関数のバリデーションテスト"""

    @pytest.fixture
    def mock_db(self):
        """データベース関連のモック"""
        from unittest.mock import patch
        with patch('lib.audit.run_query') as mock_query:
            mock_query.return_value = []
            yield mock_query

    def test_invalid_start_date_raises_error(self, mock_db):
        """無効な開始日でエラー発生"""
        from lib.audit import get_audit_logs
        from lib.validation import ValidationError

        with pytest.raises(ValidationError):
            get_audit_logs(start_date="invalid-date")

    def test_invalid_end_date_raises_error(self, mock_db):
        """無効な終了日でエラー発生"""
        from lib.audit import get_audit_logs
        from lib.validation import ValidationError

        with pytest.raises(ValidationError):
            get_audit_logs(end_date="2024-13-01")

    def test_valid_date_range(self, mock_db):
        """有効な日付範囲でエラーなし"""
        from lib.audit import get_audit_logs

        result = get_audit_logs(
            start_date="2024-01-01",
            end_date="2024-12-31"
        )
        assert isinstance(result, list)

    def test_no_filters(self, mock_db):
        """フィルタなしで呼び出し可能"""
        from lib.audit import get_audit_logs

        result = get_audit_logs()
        assert isinstance(result, list)


class TestVerifyChainIntegrityFunction:
    """verify_chain_integrity関数のテスト"""

    @pytest.fixture
    def mock_db(self):
        """データベース関連のモック"""
        from unittest.mock import patch
        with patch('lib.audit.run_query') as mock_query, \
             patch('lib.audit.run_query_single') as mock_single:
            yield mock_query, mock_single

    def test_empty_chain_is_valid(self, mock_db):
        """空のチェーンは有効"""
        mock_query, mock_single = mock_db
        mock_query.return_value = []

        from lib.audit import verify_chain_integrity

        result = verify_chain_integrity()

        assert result['is_valid'] is True
        assert result['total_entries'] == 0
        assert result['errors'] == []

    def test_result_structure(self, mock_db):
        """結果構造の確認"""
        mock_query, mock_single = mock_db
        mock_query.return_value = []

        from lib.audit import verify_chain_integrity

        result = verify_chain_integrity()

        assert 'is_valid' in result
        assert 'total_entries' in result
        assert 'first_invalid_seq' in result
        assert 'errors' in result


class TestGetChainStatusFunction:
    """get_chain_status関数のテスト"""

    def test_empty_chain_status(self):
        """空のチェーンステータス"""
        from unittest.mock import patch
        with patch('lib.audit.run_query_single') as mock_single:
            mock_single.side_effect = [
                {'total_entries': 0, 'latest_sequence': None, 'first_sequence': None},
                None
            ]

            from lib.audit import get_chain_status

            result = get_chain_status()

            assert result['total_entries'] == 0
            assert result['genesis_hash'] == GENESIS_HASH

    def test_chain_with_entries(self):
        """エントリがあるチェーンステータス"""
        from unittest.mock import patch
        with patch('lib.audit.run_query_single') as mock_single:
            mock_single.side_effect = [
                {'total_entries': 10, 'latest_sequence': 10, 'first_sequence': 1},
                {'timestamp': '2024-01-01', 'sequenceNumber': 10, 'entryHash': 'abc123'}
            ]

            from lib.audit import get_chain_status

            result = get_chain_status()

            assert result['total_entries'] == 10
            assert result['latest_sequence'] == 10
            assert result['latest_hash'] == 'abc123'
