# 邀请码社区看板

一个零后端、可部署到 GitHub Pages 的邀请码收集看板。功能与参考站点一致：统计、状态筛选、点击复制、本地“试过”标记、深色模式、移动端布局和每分钟自动刷新。

## 部署

把仓库推送到 GitHub 的 `main` 分支后，Actions 会自动部署 Pages。首次使用时在仓库 Settings → Pages 中选择 GitHub Actions。

数据只需要修改根目录的 `codes.json`；页面不需要改动。

## 数据格式

`codes` 中每项至少包含 `code`、`postedAt`、`status`，可选 `postUrl`、`author`、`replyCount`、`expires`。

状态值：`maybe_available`、`maybe_used`、`confirmed_used`。

