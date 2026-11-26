# 邀请码社区看板

一个可部署到 GitHub Pages 的邀请码社区看板。前端负责展示和本地“试过”标记，`scripts/patrol.py` 负责把浏览器采集的公开帖子筛选、抽码、去重、判断状态并提交回 `codes.json`。

## 部署

把仓库推送到 GitHub 的 `main` 分支后，Actions 会自动部署 Pages。首次使用时在仓库 Settings → Pages 中选择 GitHub Actions。

数据只需要修改根目录的 `codes.json`；页面不需要改动。

## 扫描与更新

仓库每 10 分钟同步两个对标站点的公开 `codes.json`：

- `https://good1uck.github.io/xiaodou-codes/codes.json`
- `https://paipiange.github.io/xiaodou-codes/codes.json`

同步时按邀请码统一转大写并去重，保留较新的记录；每次同步前会验收源站 HTTP、JSON 结构、邀请码格式和单源重复，GitHub Pages 部署完成后还会验收线上发布数据是否包含两个源的并集。

参考站点同样不是网页直接调用 X API，而是先由已登录浏览器/采集器整理帖子 JSON，再交给巡检脚本处理。帖子 JSON 可以是数组，也可以是 `{ "posts": [...] }`，字段示例见 `posts.example.json`。

```powershell
python scripts/patrol.py --self-test --codes-json codes.json
python scripts/patrol.py --posts posts.json --dry-run
$env:GITHUB_TOKEN = "你的仓库 Contents 写权限令牌"
python scripts/patrol.py --posts posts.json

python scripts/sync_target_codes.py --self-test
python scripts/acceptance.py
```

脚本会过滤求码帖、卖码广告、汇总帖、接力空帖、转发和其他产品的邀请码；新码放到前面，并根据回访帖的回复数更新 `maybe_used` 状态。不要把 `GITHUB_TOKEN` 写入仓库。

## 数据格式

`codes` 中每项至少包含 `code`、`postedAt`、`status`，可选 `postUrl`、`author`、`replyCount`、`expires`。

状态值：`maybe_available`、`maybe_used`、`confirmed_used`。

