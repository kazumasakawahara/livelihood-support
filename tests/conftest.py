"""
テスト共通設定
pytest-asyncioの設定とフィクスチャ
"""

import pytest


# pytest-asyncio設定
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session")
def event_loop_policy():
    """イベントループポリシーを設定"""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()
