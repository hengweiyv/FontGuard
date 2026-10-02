# FontGuard 0.2.0 服务器验证

**简体中文** | [English](server-verification.md) | [返回首页](../README.md)

验证日期：2026-10-02。在 Ubuntu 24.04 服务器上使用基于 `python:3.11-slim` 的独立 Docker 容器测试，未发布应用端口。扫描阶段使用 `--network=none`；构建镜像时安装依赖需要联网。测试未修改服务器生产应用配置。

## 实际结果

将 8 个真实上游 TTF 文件改为带公司前缀的文件名后，运行镜像仍正确识别全部字体，并全部匹配数据库记录的 SHA256。二进制来源详见 `data/imports/verified-hashes.json`。

- Python 3.11.17：**72 项测试通过，耗时 40.50 秒**，测试网络关闭。
- 真实 TTF、WOFF、WOFF2、子集/嵌入 PDF、原生 DOCX、原生 PPTX、CSS、HTML、SVG 验收：**通过**。
- 8 个改名的真实 TTF 文件精确哈希匹配：**通过**。
- 缓存复用、基线抑制与新增发现、禁用策略：**通过**。
- 终端/JSON 的 0/1/2 退出码及完整 SARIF schema：**通过**。
- 运行镜像在 512 MiB、单 CPU 限制下完成 8 个真实字体的离线扫描：**通过**。

原生文件验收最初发现 HTML 行内样式边界问题：缺少末尾 CSS 分号时，标签尾部被误读进字体名。随后修复解析器、更新分析缓存版本，并新增 3 项策略/行号回归测试。以上结果来自修复后的 wheel 和全新的验收目录。

最终服务器镜像将修复后的 wheel 离线安装到此前已构建的依赖镜像中；另由 GitHub CI 从仓库 Dockerfile 构建源码并完成禁网测试。

## 复现步骤

构建发布源码归档，并显式下载 8 个测试字体：

```sh
python -m pip install '.[dev]'
python scripts/fetch_test_fonts.py
python -m build
tar -czf artifacts/e2e-fonts.tar.gz -C artifacts/e2e fonts
```

将 `dist/fontguard-0.2.0.tar.gz`、`artifacts/e2e-fonts.tar.gz` 和 `scripts/server_test.sh` 复制到服务器独立测试目录，再执行：

```sh
sh server_test.sh "$HOME/fontguard-tests/2026-10-02"
```

脚本构建独立测试镜像，以 1 GiB 内存、单 CPU 限制运行 pytest，并创建原生 PDF、DOCX、PPTX 与转换后的 WOFF、WOFF2 文件。验收还检查本地 CSS 字体解析、HTML、SVG、缓存、基线变化、禁用策略、损坏字体、退出码及完整 SARIF 校验。

运行镜像扫描限制为 512 MiB 和单 CPU。这些是测试参数，不是经过测量的最低运行要求或吞吐量承诺。

复现运行的报告保存在脚本输出的验收目录中。每次运行使用新目录，避免旧缓存和策略影响结果。公开仓库及发布归档不包含第三方字体二进制。

## 本次服务器环境清理

验收完成后，按服务器所有者要求删除了本次专用测试目录，包括测试字体、原生测试文件、缓存、报告、安装归档和脚本。FontGuard 镜像、对应构建中间层及本次下载的 Python 3.11 基础镜像也已删除，共清理 25 个镜像记录。

核验原有 23 个容器状态未改变，其中 15 个继续运行；原有数据卷和网络未改变，生产服务配置未修改。本地报告和公开 GitHub 项目保留。此处记录的是已完成的验证，不表示服务器上仍保留 FontGuard 环境；再次运行需要重新准备。
