#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同步目标站点公开邀请码数据，并按 code 去重合并到本仓库的 codes.json。

这个脚本只读取公开的 JSON，不需要 X 登录、Cookie 或 API Key。
GitHub Actions 每 10 分钟调用一次；只有数据发生变化时才会产生提交。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen


BEIJING = timezone(timedelta(hours=8))
DEFAULT_SOURCE = "https://good1uck.github.io/xiaodou-codes/codes.json"


def read_json_url(url: str) -> dict:
    request = Request(
        url,
        headers={
            "User-Agent": "invite-code-board-target-sync/1.0",
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("codes"), list):
        raise ValueError("目标 JSON 缺少 codes 数组")
    return payload


def timestamp(item: dict) -> str:
    return str(item.get("postedAtUtc") or item.get("postedAt") or "")


def numeric_id(value: object) -> int:
    try:
        return int(str(value or "0"))
    except ValueError:
        return 0


def merge_codes(target: dict, local: dict) -> tuple[dict, int]:
    """合并目标和本地数据，按邀请码唯一；重复时保留较新的记录。"""
    merged: dict[str, dict] = {}
    duplicate_count = 0

    # 目标数据先入库，本地数据再覆盖同码的旧记录，避免丢失我们刚采集的最新状态。
    for item in [*(target.get("codes") or []), *(local.get("codes") or [])]:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip().upper()
        if not code:
            continue
        current = merged.get(code)
        candidate = {**item, "code": code}
        if current is None:
            merged[code] = candidate
            continue
        duplicate_count += 1
        current_time = timestamp(current)
        candidate_time = timestamp(candidate)
        # 选时间较新的；时间相同则优先本地记录，方便保留本仓库的状态字段。
        if candidate_time >= current_time:
            merged[code] = candidate

    codes = sorted(merged.values(), key=timestamp, reverse=True)
    source_since = numeric_id(target.get("lastSinceId"))
    local_since = numeric_id(local.get("lastSinceId"))
    last_since = max(source_since, local_since)
    result = {
        "lastUpdated": datetime.now(BEIJING).strftime("%Y-%m-%d %H:%M") + " 北京时间",
        "lastSinceId": str(last_since),
        "codes": codes,
    }
    return result, duplicate_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-url", default=DEFAULT_SOURCE)
    parser.add_argument("--output", default="codes.json")
    args = parser.parse_args()

    output_path = Path(args.output)
    local = json.loads(output_path.read_text(encoding="utf-8"))
    target = read_json_url(args.source_url)
    merged, duplicate_count = merge_codes(target, local)

    old_text = output_path.read_text(encoding="utf-8")
    new_text = json.dumps(merged, ensure_ascii=False, indent=2) + "\n"
    if json.loads(old_text) == merged:
        print(f"没有变化：本地 {len(local.get('codes') or [])} 条，目标 {len(target['codes'])} 条，重复 {duplicate_count} 条")
        return 0

    output_path.write_text(new_text, encoding="utf-8")
    print(f"已合并：本地 {len(local.get('codes') or [])} 条 + 目标 {len(target['codes'])} 条")
    print(f"去重 {duplicate_count} 条，最终 {len(merged['codes'])} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())

