#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同步两个目标站点公开邀请码数据，并按 code 去重合并到本仓库的 codes.json。

这个脚本只读取公开的 JSON，不需要 X 登录、Cookie 或 API Key。
GitHub Actions 每 10 分钟调用一次；只有数据发生变化时才会产生提交。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen


BEIJING = timezone(timedelta(hours=8))
DEFAULT_SOURCES = [
    "https://good1uck.github.io/xiaodou-codes/codes.json",
    "https://paipiange.github.io/xiaodou-codes/codes.json",
]
CODE_RE = re.compile(r"^(?:[A-Z0-9]{4,16}|[A-Z0-9]{1,16}-[A-Z0-9]{1,8})$")


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


def validate_source(url: str, payload: dict) -> tuple[int, int]:
    """校验公开源的基本真实性：可访问、结构正确、邀请码格式合法且不重复。"""
    items = payload.get("codes") or []
    seen: set[str] = set()
    invalid: list[str] = []
    duplicate = 0
    for item in items:
        if not isinstance(item, dict):
            invalid.append("<非对象>")
            continue
        code = str(item.get("code") or "").strip().upper()
        if not CODE_RE.fullmatch(code):
            invalid.append(code or "<空码>")
        if code in seen:
            duplicate += 1
        seen.add(code)
    if invalid:
        raise ValueError(f"{url} 含非法邀请码格式: {invalid[:5]}")
    if duplicate:
        raise ValueError(f"{url} 含 {duplicate} 条重复邀请码")
    return len(items), len(seen)


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


def merge_sources(sources: list[tuple[str, dict]], local: dict) -> tuple[dict, int]:
    """先合并多个公开源，再与本地数据合并；所有源按邀请码唯一。"""
    combined: dict = {"codes": [], "lastSinceId": "0"}
    for url, payload in sources:
        count, _unique = validate_source(url, payload)
        combined["codes"].extend(payload.get("codes") or [])
        combined["lastSinceId"] = str(max(
            numeric_id(combined.get("lastSinceId")),
            numeric_id(payload.get("lastSinceId")),
        ))
    merged, duplicate_count = merge_codes(combined, local)
    return merged, duplicate_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-url",
        action="append",
        dest="source_urls",
        help="公开 codes.json 地址，可重复传入；缺省同步两个对标站点",
    )
    parser.add_argument("--output", default="codes.json")
    parser.add_argument("--self-test", action="store_true", help="抓取两个公开源并做真实性/去重验收，不写文件")
    args = parser.parse_args()

    source_urls = args.source_urls or DEFAULT_SOURCES
    sources: list[tuple[str, dict]] = []
    for url in source_urls:
        try:
            payload = read_json_url(url)
            count, unique = validate_source(url, payload)
            print(f"源验收通过：{url}，{count} 条，单源唯一 {unique} 条")
            sources.append((url, payload))
        except Exception as exc:
            print(f"源验收失败：{url}: {exc}", file=sys.stderr)
            return 2

    if args.self_test:
        codes = [str(item.get("code") or "").upper() for _, payload in sources for item in payload.get("codes") or []]
        print(f"真实性验收通过：{len(sources)} 个源，{len(codes)} 条源数据，合并去重后 {len(set(codes))} 条")
        return 0

    output_path = Path(args.output)
    local = json.loads(output_path.read_text(encoding="utf-8"))
    merged, duplicate_count = merge_sources(sources, local)

    # 目标站点的 lastUpdated 可能变化，但如果邀请码和状态都没变化，
    # 不要为了时间戳制造一条无意义的 Git 提交。
    if (
        local.get("codes") == merged.get("codes")
        and str(local.get("lastSinceId")) == str(merged.get("lastSinceId"))
    ):
        print(f"没有变化：本地 {len(local.get('codes') or [])} 条，双源 {sum(len(p.get('codes') or []) for _, p in sources)} 条，重复 {duplicate_count} 条")
        return 0

    new_text = json.dumps(merged, ensure_ascii=False, indent=2) + "\n"
    output_path.write_text(new_text, encoding="utf-8")
    print(f"已合并：本地 {len(local.get('codes') or [])} 条 + 双源 {sum(len(p.get('codes') or []) for _, p in sources)} 条")
    print(f"去重 {duplicate_count} 条，最终 {len(merged['codes'])} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())

