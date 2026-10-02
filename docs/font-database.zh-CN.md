# 字体数据库来源与范围

**简体中文** | [English](font-database.md) | [返回首页](../README.md)

FontGuard 0.2.0 包含 2,052 条字体家族记录，并不表示独立验证了 2,052 个二进制构建。数据库保存了 8 个代表性上游 TTF 文件的精确 SHA256 指纹；其他二进制仍需要名称匹配、版本和来源核查。

## 官方 Google Fonts 导入

上游仓库：[google/fonts](https://github.com/google/fonts)。

固定快照：`9710da1eacb3be272583c3224dcb70f9da6eadbb`。

完整 Git 树含 2,031 个家族元数据文件。导入器下载每个候选条目的 `METADATA.pb` 和该家族自己的许可文本，核对声明许可与文件是否一致，导入 2,020 个经过核查的家族。Google Fonts 目录标记为分发方，不推定其为设计者或版权所有者；来源清单保留署名设计者和字体文件名。

既有的 Noto Sans 记录得到补充，没有重复新增；思源黑体保留直接来自 Adobe 的来源。

导入支持 OFL-1.1、Apache-2.0 和 Ubuntu-font-1.0。创作及渲染输出权限与分发、嵌入条件分别处理。具体条件仍以原始许可和保留字体名称（Reserved Font Names）为准。FontGuard 没有把第三方字体重新授权为 Apache-2.0。

`data/imports/google-fonts.json` 记录固定上游提交、各家族元数据和许可文件的 SHA256、来源路径、排除条目及删除的歧义别名。11 个条目因缺少家族许可文件或属于退役的 `_todelist` 重复项而排除。Protobuf 的 C 风格转义名称在不执行代码的前提下解析；有歧义的完整名称别名在校验前省略。

维护者显式联网导入：

```sh
mkdir -p artifacts
curl -fsSL 'https://api.github.com/repos/google/fonts/git/trees/9710da1eacb3be272583c3224dcb70f9da6eadbb?recursive=1' -o artifacts/google-fonts-tree.json
python scripts/import_google_fonts.py --tree artifacts/google-fonts-tree.json --allow-exclusions
python scripts/fetch_test_fonts.py
fontguard database validate
```

通过 GitHub Git Trees API 获取完整上游树并保留提交 SHA。导入属于维护操作；普通扫描不会更新数据库，也不会访问 Google。提交更新前审核 YAML 和来源清单的变化。

`data/imports/verified-hashes.json` 记录 8 个真实字体的精确源 URL、字节数及 SHA256：Kosugi、Roboto Slab、JetBrains Mono、Lato、Lobster、Long Cang、Noto Sans 和 Ubuntu。测试二进制留在忽略的 `artifacts/` 中，不包含在公开源码仓库中。重新导入时保留已有哈希。

## Windows 分发字体

31 个常见 Windows 字体家族引用各自的微软官方字体页面和 Windows 字体再分发 FAQ。中文别名覆盖微软雅黑、微软正黑体、宋体/新宋体、黑体、楷体、仿宋和等线。分发方标签不表示微软拥有每个字体的版权。

`LicenseRef-Windows-Fonts` 是描述 Windows 软件条款及潜在扩展权利的本地许可引用，并非虚构的 SPDX 开源许可。这些事实仅适用于 Windows 随附的版本。

拥有适当软件授权时，制作商业渲染输出可能被允许；但无法从文档验证软件使用权，因此这类用途需要 `REVIEW`。仅在 CSS 后备字体列表中列出名称可以允许；自行托管字体文件、应用嵌入和再分发需要分别核查。文档嵌入标志和创作软件条款也有影响。导入器不下载或再分发 Windows 字体二进制。

官方来源：[微软字体 FAQ](https://learn.microsoft.com/en-us/typography/fonts/font-faq)。

`data/imports/windows-fonts.json` 保留来源页面哈希及核查日期。可复现导入脚本为 `scripts/import_windows_fonts.py`。
