"""
生活保護受給者尊厳支援データベース - Neo4j接続モジュール
Manifesto: Livelihood Protection Support & Dignity Graph 準拠

Neo4j接続管理とクエリ実行ヘルパー
"""

import os
import sys
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()


def log(message: str, level: str = "INFO"):
    """ログ出力（標準エラー出力）"""
    sys.stderr.write(f"[DB:{level}] {message}\n")
    sys.stderr.flush()


# --- Neo4j 接続 ---
_driver = None


def get_driver():
    """Neo4jドライバーを取得（シングルトン）"""
    global _driver
    if _driver is None:
        uri = os.getenv("NEO4J_URI")
        username = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")

        if not all([uri, username, password]):
            raise RuntimeError("NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD環境変数が必要です")

        _driver = GraphDatabase.driver(uri, auth=(username, password))
        log(f"Neo4j接続確立: {uri}")

    return _driver


def close_driver():
    """Neo4jドライバーをクローズ"""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
        log("Neo4j接続クローズ")


def run_query(query: str, params: dict = None) -> list:
    """
    Cypherクエリ実行ヘルパー

    Args:
        query: Cypherクエリ文字列
        params: クエリパラメータ

    Returns:
        クエリ結果のリスト
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]


def run_query_single(query: str, params: dict = None) -> dict | None:
    """
    単一結果を返すCypherクエリ実行

    Args:
        query: Cypherクエリ文字列
        params: クエリパラメータ

    Returns:
        最初の結果、またはNone
    """
    results = run_query(query, params)
    return results[0] if results else None
