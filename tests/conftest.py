"""
テスト共通設定
pytest-asyncioの設定とフィクスチャ

Note:
- pytest-asyncioはasync testに必要
- E2Eテスト（tests/e2e/）はPlaywright同期APIを使用
- E2Eテストと単体テストを同時に実行すると、イベントループの競合が発生するため、
  別々に実行することを推奨:
    - 単体テスト: uv run pytest --ignore=tests/e2e
    - E2Eテスト: uv run pytest tests/e2e
"""

import pytest


# pytest-asyncio設定
pytest_plugins = ("pytest_asyncio",)
