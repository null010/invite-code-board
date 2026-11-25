# 巡检流程

本仓库现在包含与参考站点同类的 `scripts/patrol.py` 数据处理链路：

1. 由已登录浏览器或其他采集器导出 X 公开帖子 JSON。
2. `patrol.py` 抽取小豆邀请码。
3. 过滤求码帖、卖码广告、汇总帖、接力空帖、转发和其他产品邀请码。
4. 按 code 去重，按回复数更新状态。
5. 使用 `GITHUB_TOKEN` 通过 Contents API 更新根目录 `codes.json`。
6. GitHub Pages 工作流继续负责发布网站。

示例：

```powershell
python scripts/patrol.py --posts posts.example.json --dry-run
$env:GITHUB_TOKEN = "你的 invite-code-board Contents 写权限令牌"
python scripts/patrol.py --posts posts.json
```

当前仓库没有保存 X 登录态或 API 密钥，因此不会擅自实现登录抓取。要达到参考站点的 252 条实时数据，还需要把已登录浏览器采集器接到 `posts.json` 输入端。