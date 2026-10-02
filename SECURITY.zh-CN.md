# 安全说明

**简体中文** | [English](SECURITY.md) | [返回首页](README.md)

FontGuard 会解析可能不可信的文件。请及时更新依赖，并让 CI 使用完成任务所需的最小权限。扫描器跳过文件系统符号链接、限制文件大小和 Office XML 展开规模、禁用 XML 外部实体，且扫描时不会获取远程 URL。这些检查不能替代完整的解析器沙箱；处理恶意输入时应使用隔离进程或容器。

`.fontguard.yml`、`fontguard.lock`、基线和本地缓存属于受信任的组织输入，应通过代码审核保护。扫描不可信工作区时使用 `--no-cache`。分析器插件会执行 Python 代码，仅在明确启用 `--plugins` 后加载。

## 报告安全问题

请通过 [GitHub 仓库 Security 页](https://github.com/hengweiyv/FontGuard/security)的私密漏洞报告功能，向维护者提交可复现的安全问题。不要在公开 issue 中上传包含私人数据的攻击文档。

本项目没有官方安全邮箱，也未承诺固定响应时限。报告时请说明受影响版本、复现步骤和实际影响，并使用不含敏感信息的最小测试文件。
