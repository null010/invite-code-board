#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""线上真实性验收：验证两个公开源和本 GitHub Pages 发布数据。"""

from __future__ import annotations

import json
from urllib.request import Request, urlopen


SOURCES = [
    "https://good1uck.github.io/xiaodou-codes/codes.json",
    "https://paipiange.github.io/xiaodou-codes/codes.json",
]
PUBLISHED = "https://null010.github.io/invite-code-board/codes.json"


def fetch(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "invite-code-board-acceptance/1.0"})
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"{url} HTTP {response.status}")
        data = json.load(response)
    if not isinstance(data, dict) or not isinstance(data.get("codes"), list):
        raise RuntimeError(f"{url} 缺少 codes 数组")
    return data


def codes(data: dict) -> set[str]:
    result = {str(item.get("code") or "").strip().upper() for item in data["codes"] if isinstance(item, dict)}
    if "" in result:
        raise RuntimeError("发现空邀请码")
    return result


def main() -> int:
    source_sets = [codes(fetch(url)) for url in SOURCES]
    published = codes(fetch(PUBLISHED))
    union = set().union(*source_sets)
    if len(published) != len(fetch(PUBLISHED)["codes"]):
        raise RuntimeError("线上发布的 codes.json 含重复邀请码")
    missing = sorted(union - published)
    if missing:
        raise RuntimeError(f"线上发布缺少 {len(missing)} 个双源邀请码: {missing[:10]}")
    print(f"真实性验收通过：{len(SOURCES)} 个源，源合计去重 {len(union)} 条，线上发布 {len(published)} 条，缺失 0 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

