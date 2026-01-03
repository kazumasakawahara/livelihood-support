"""
lib/db_connection.py のユニットテスト
Neo4j接続管理のテスト
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

from lib.db_connection import (
    log,
    get_driver,
    close_driver,
    run_query,
    run_query_single,
)


class TestLog:
    """log関数のテスト"""

    def test_log_info(self, capsys):
        """INFOログ出力"""
        log("テストメッセージ")
        captured = capsys.readouterr()
        assert "[DB:INFO] テストメッセージ" in captured.err

    def test_log_error(self, capsys):
        """ERRORログ出力"""
        log("エラーメッセージ", level="ERROR")
        captured = capsys.readouterr()
        assert "[DB:ERROR] エラーメッセージ" in captured.err


class TestGetDriver:
    """get_driver関数のテスト"""

    def test_missing_env_vars(self):
        """環境変数不足でエラー"""
        with patch.dict(os.environ, {}, clear=True):
            # Reset _driver
            import lib.db_connection
            lib.db_connection._driver = None

            with pytest.raises(RuntimeError) as exc_info:
                get_driver()

            assert "NEO4J_URI" in str(exc_info.value)

    @patch('lib.db_connection.GraphDatabase.driver')
    def test_creates_driver(self, mock_driver_class):
        """ドライバー作成"""
        mock_driver = MagicMock()
        mock_driver_class.return_value = mock_driver

        env = {
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USERNAME": "neo4j",
            "NEO4J_PASSWORD": "password"
        }
        with patch.dict(os.environ, env):
            import lib.db_connection
            lib.db_connection._driver = None

            driver = get_driver()

            assert driver is mock_driver
            mock_driver_class.assert_called_once_with(
                "bolt://localhost:7687",
                auth=("neo4j", "password")
            )

    @patch('lib.db_connection.GraphDatabase.driver')
    def test_returns_existing_driver(self, mock_driver_class):
        """既存ドライバーを返す"""
        mock_driver = MagicMock()

        import lib.db_connection
        lib.db_connection._driver = mock_driver

        driver = get_driver()

        assert driver is mock_driver
        mock_driver_class.assert_not_called()


class TestCloseDriver:
    """close_driver関数のテスト"""

    def test_close_existing_driver(self):
        """既存ドライバーをクローズ"""
        mock_driver = MagicMock()

        import lib.db_connection
        lib.db_connection._driver = mock_driver

        close_driver()

        mock_driver.close.assert_called_once()
        assert lib.db_connection._driver is None

    def test_close_none_driver(self):
        """ドライバーがNoneの場合"""
        import lib.db_connection
        lib.db_connection._driver = None

        # エラーなく完了
        close_driver()

        assert lib.db_connection._driver is None


class TestRunQuery:
    """run_query関数のテスト"""

    @patch('lib.db_connection.get_driver')
    def test_run_query_success(self, mock_get_driver):
        """クエリ実行成功"""
        mock_record1 = MagicMock()
        mock_record1.data.return_value = {"name": "山田太郎"}
        mock_record2 = MagicMock()
        mock_record2.data.return_value = {"name": "鈴木花子"}

        mock_result = [mock_record1, mock_record2]
        mock_session = MagicMock()
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session
        mock_get_driver.return_value = mock_driver

        result = run_query("MATCH (n) RETURN n", {"limit": 10})

        assert len(result) == 2
        assert result[0]["name"] == "山田太郎"
        assert result[1]["name"] == "鈴木花子"
        mock_session.run.assert_called_once_with("MATCH (n) RETURN n", {"limit": 10})

    @patch('lib.db_connection.get_driver')
    def test_run_query_empty_result(self, mock_get_driver):
        """空の結果"""
        mock_result = []
        mock_session = MagicMock()
        mock_session.run.return_value = mock_result
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session
        mock_get_driver.return_value = mock_driver

        result = run_query("MATCH (n) RETURN n")

        assert result == []

    @patch('lib.db_connection.get_driver')
    def test_run_query_default_params(self, mock_get_driver):
        """パラメータなしでもデフォルト空辞書"""
        mock_session = MagicMock()
        mock_session.run.return_value = []
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_driver = MagicMock()
        mock_driver.session.return_value = mock_session
        mock_get_driver.return_value = mock_driver

        run_query("MATCH (n) RETURN n")

        mock_session.run.assert_called_once_with("MATCH (n) RETURN n", {})


class TestRunQuerySingle:
    """run_query_single関数のテスト"""

    @patch('lib.db_connection.run_query')
    def test_returns_first_result(self, mock_run_query):
        """最初の結果を返す"""
        mock_run_query.return_value = [
            {"name": "山田太郎"},
            {"name": "鈴木花子"}
        ]

        result = run_query_single("MATCH (n) RETURN n", {"id": 1})

        assert result == {"name": "山田太郎"}
        mock_run_query.assert_called_once_with("MATCH (n) RETURN n", {"id": 1})

    @patch('lib.db_connection.run_query')
    def test_returns_none_for_empty(self, mock_run_query):
        """結果が空の場合Noneを返す"""
        mock_run_query.return_value = []

        result = run_query_single("MATCH (n) RETURN n")

        assert result is None
