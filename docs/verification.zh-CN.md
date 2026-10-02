# 本机验证记录 — 2026-10-02

**简体中文** | [English](verification.md) | [返回首页](../README.md)

环境为 Windows，使用 Codex 随附运行时中的 Python 3.12.14 和项目独立 `.venv`，未替换用户的全局 Python 安装。

## 初始 0.1.0 本地原型

以下是初始阶段的历史记录，后续 0.2.0 和服务器验证见下文。

- `python -m pytest -q`：63 项测试通过。
- `python -m ruff check .`、`python -m ruff format --check .`：通过。
- `python -m mypy`：36 个库源码文件通过严格类型检查。
- `fontguard database validate`：2 条官方来源字体记录通过校验。
- `python -m pip check`：未发现损坏的依赖要求。
- `python -m build`：成功生成 wheel 和源码包。
- 使用 `pip install --no-index --no-deps --target artifacts/wheel-install dist/fontguard-0.1.0-py3-none-any.whl` 离线安装 wheel。
- `python tests/release_smoke.py artifacts/wheel-install`：确认导入来自已安装的 wheel 及其内置数据库，不是可编辑源码。该冒烟测试复用了开发环境依赖；扫描阶段禁止网络连接。JSON、SARIF、HTML、终端输出及退出码 0/1/2 均通过检查。
- SARIF 对照仓库保留的完整 OASIS 2.1.0 schema 校验，包括基线抑制信息；测试及发布冒烟扫描离线运行。
- 完成全项目 CLI 扫描，使用 `--usage webfont --fail-on high --no-cache`。

分析器测试生成原创 TTF、OTF、WOFF、WOFF2 字体，以及包含嵌入字体和标准字体的真实 PDF。此阶段 Office 测试使用合成 ZIP/XML 文件包，检查主题、样式和东亚字体声明，未声称在 Word 或 PowerPoint 中进行视觉验证。

测试还覆盖了异常 XML、缺失的字体引用、加密 PDF、CSS 依赖缓存失效、分层忽略、策略优先级、基线变化、按范围限定的哈希审批、Git 差异和 Unicode 命令行输出。

本地示例报告位于 `artifacts/sample-report.*`，发布归档位于 `dist/`；这两个目录被 Git 和扫描器忽略。

初始原型阶段尚未执行 Docker、远程 GitHub Actions、Linux/macOS 运行验证或 GitHub SARIF 上传，也未发布 PyPI 包或镜像仓库镜像。当时仅包含思源黑体和 Noto Sans；未收录字体保持未知。后续测试状态见下面两节。

## 扩展后的 0.2.0 本机验证

- 数据库包含 2,052 个家族、5,837 个精确名称/别名、8 个真实二进制 SHA256；45 个有歧义的规范化键不用于回退。
- `python -m pytest -q --tb=short`：Windows 上 **72 项测试通过，耗时 60.18 秒**，包含服务器验收期间新增的 3 项 HTML 行内样式策略回归测试。
- 源码、测试和维护脚本通过 Ruff 代码及格式检查。
- 全部 36 个库源码文件通过严格 mypy 检查。
- 目录导入、地区家族身份、策略/去重/基线隔离和 Protobuf 单引号转义均有回归测试。
- Linux/Docker 与原生文件验收详见[服务器验证记录](server-verification.zh-CN.md)。
- 最终发布包使用 Hatchling 1.32.4 和 `python -m build --no-isolation` 构建；已安装 wheel 的离线扫描及完整 SARIF 校验通过。额外的隔离构建尝试遇到构建依赖的 TLS/索引下载错误，因此本地发布归档使用已安装的构建后端。

## 公开仓库 CI

发布提交 `d082897020e4f54da7521da829cbd35239842bcc` 的 [GitHub Actions 运行](https://github.com/hengweiyv/FontGuard/actions/runs/36964651723)已完成，10 个任务全部成功：Windows、macOS、Linux × Python 3.11、3.12、3.13 的 9 组检查，以及 Docker 源码构建和禁网测试。

CI 中的依赖安装和隔离构建均成功。该结果不等于已验证 GitHub Code Scanning 的 SARIF 上传，也不表示已发布到 PyPI 或镜像仓库。
