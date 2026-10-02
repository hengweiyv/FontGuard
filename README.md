# FontGuard 字体卫士

**简体中文** | [English](README.en.md)

面向开发者与设计师的字体授权合规扫描工具。

发现项目中的字体，识别授权来源，并在 CI 中执行团队的字体使用策略。

本地运行 · 离线扫描 · 开源 · 命令行优先 · 支持 CI

```sh
fontguard scan .
fontguard scan poster.pdf --usage commercial_design
fontguard scan ./website --usage webfont --fail-on high --format sarif --output fontguard.sarif
```

FontGuard 0.2.0 无需账号，扫描时无需上传文件或连接服务器。报告包含字体元数据、可能的身份、授权来源与组织策略冲突。识别到商业字体，并不意味着使用者没有购买授权。

## 安装

需要 **Python 3.11 或更新版本**。本项目尚未发布到 PyPI，直接执行 `pip install fontguard` 可能安装到其他同名软件。请从本仓库安装：

```sh
git clone https://github.com/hengweiyv/FontGuard.git
cd FontGuard
python -m venv .venv
# Windows PowerShell 激活环境：.\.venv\Scripts\Activate.ps1
# Linux/macOS 激活环境：source .venv/bin/activate
python -m pip install .
fontguard --version
```

也可以在仓库目录执行 `pipx install .` 或 `uv tool install .`。安装依赖需要联网，除非已准备离线 wheel 包。扫描和数据库校验均可离线运行。

[GitHub Releases](https://github.com/hengweiyv/FontGuard/releases/tag/v0.2.0) 提供 wheel、源码包及 SHA256 校验文件。下载 wheel 后可执行：

```sh
python -m pip install ./fontguard-0.2.0-py3-none-any.whl
```

未来确认 PyPI 名称可用并完成发布后，才适合使用 `pip install fontguard`、`pipx install fontguard` 或 `uv tool install fontguard`。

## 快速开始

```sh
fontguard scan examples/site.css --usage commercial_design --no-cache
```

示例包含思源黑体（Source Han Sans）、Noto Sans 和一个未知品牌字体。前两者有已记录的 OFL 授权信息；未知字体需要进一步核查。发布浏览器字体文件时，使用 `--usage webfont` 查看分发条件。未指定 `--usage` 时，已识别字体也会因用途不明确而进入 `REVIEW`。

## 命令行用法

```sh
fontguard scan PATH --usage webfont --fail-on high
fontguard scan . --format json --output report.json
fontguard scan . --format html --output report.html
fontguard scan . --fail-on high --fail-on unknown
fontguard scan . --baseline .fontguard-baseline.json
fontguard scan . --git-diff
fontguard scan . --git-diff origin/main
fontguard scan . --config company.yml --database ./data --workers 4 --no-cache
fontguard baseline create . --usage webfont
fontguard database validate
fontguard allow assets/brand.ttf --usage webfont --reason "已记录企业授权" --approved-by legal-team
```

退出码：**0** 表示通过；**1** 表示出现所选阈值覆盖的风险；**2** 表示扫描不完整、配置或数据库无效、I/O 错误等运行问题。JSON 和 SARIF 同样包含错误信息；损坏文件和受密码保护的 PDF 不会被静默判定为通过。命令行重复指定的 `--fail-on` 会替换配置文件中的阈值。

| 阈值 | 触发退出码 1 的风险 |
| --- | --- |
| `high`（默认） | HIGH |
| `review` | REVIEW、HIGH |
| `low` | LOW、REVIEW、HIGH |
| `safe` | SAFE、LOW、REVIEW、HIGH |
| `unknown` | 仅 UNKNOWN |

`UNKNOWN` 是独立类别。需要同时拦截高风险和未知字体时，使用 `--fail-on high --fail-on unknown`。报告统计的是“来源文件中的字体观察记录”，并非整个项目去重后的字体家族数量。

用途参数包括：`unknown`（未明确）、`personal`（个人使用）、`commercial_design`（商业设计）、`print`（印刷）、`advertising`（广告）、`website`（网站设计）、`webfont`（浏览器字体文件）、`video`（视频）、`logo`（标志）、`ebook`（电子书）、`document_embedding`（文档嵌入）、`app_embedding`（应用嵌入）、`software_distribution`（软件分发）、`font_redistribution`（字体再分发）。

`website` 表示网站设计用途；向浏览器提供字体文件应选择 `webfont`。用途由使用者明确声明，工具不会仅凭检测到嵌入行为自动选择用途。

## 支持的文件格式

| 扫描目标 | 提取的证据 |
| --- | --- |
| TTF、OTF、WOFF、WOFF2 | 指定的 name ID 0–14、16/17，SHA256，OS/2 fsType |
| PDF | 基础字体名、子集前缀、页码、xref、嵌入字节和可读取元数据 |
| DOCX、PPTX | 内容、样式、表格、幻灯片、母版、主题中的 ZIP/XML 字体声明 |
| SVG | font-family 属性及 CSS 声明 |
| CSS、SCSS、LESS | font-family、@font-face、本地字体 URL |
| HTML、Vue、JS/TS、JSX/TSX、Svelte | CSS、常见字面量 fontFamily 属性、字体路径引用 |
| 目录 | 按扩展名递归扫描，支持分层忽略规则 |

网页分析采用保守的静态提取。动态表达式、CSS `font` 简写和复杂嵌套规则可能需要人工复核；通用 CSS 字体族会被忽略。`@font-face` 的本地引用在扫描根目录内时，可将别名关联到实际字体元数据。远程 URL、data URL 和以 `/` 开头的根路径 URL 不会被下载。未验证的文件名引用仍为 `UNKNOWN`。

PDF 中 Type 1 或仅 CFF 字体的元数据可能有限。Office 结果可能包含已声明但未使用的后备字体、主题字体；当前不解码混淆的 Office 内嵌字体，也不精确解析主题字体到每个文本片段的映射。转曲和栅格化文字无法识别。GUI、视觉识别、PSD、Figma 和视频分析属于后续扩展方向。

## 风险等级

| 等级 | 含义 |
| --- | --- |
| SAFE | 已记录的授权允许匹配字体用于指定用途 |
| LOW | 需要遵守授权条件，或已记录限定范围的组织审批 |
| REVIEW | 需要核查授权，或尚未明确用途 |
| HIGH | 明确的授权许可冲突或组织策略冲突 |
| UNKNOWN | 身份或相关许可尚未确认 |

名称匹配有置信度，但不能证明字体来源。字体内部的授权文本会保留为证据，不会自动成为可信的数据库授权事实。数据库有匹配的 SHA256 时优先使用哈希。修改文件名不会改变内部身份或哈希；改写元数据会改变哈希，也可能影响名称识别。

数据库包含 **2,052 个家族和 8 个已验证的二进制哈希**。Windows 随附的专有字体通常需要复核软件使用权及扩展授权；数据库未收录的商业字体仍为 `UNKNOWN`。

## 团队策略与忽略规则

工具在扫描根目录自动查找 `.fontguard.yml`；扫描单个文件时，根目录为该文件的父目录。

```yaml
version: 1
policy:
  fail_on: [HIGH, UNKNOWN]
  allowed_licenses: [OFL-1.1, Apache-2.0]
  denied_fonts: [Example Font]
  allowed_fonts: []
  unknown_font:
    action: unknown # 可选值：unknown | review | high
```

非空的 `allowed_fonts` 是排他性的允许列表，但列入其中不能证明拥有授权。禁用规则优先。启用许可允许列表后，列表外的已知许可会触发 `HIGH`。未知许可保持 `UNKNOWN`，除非通过 `unknown_font.action` 提高等级。无效或拼错的字段会导致配置校验失败。

遍历目录时会读取各层 `.gitignore` 和 `.fontguardignore`；同层后者优先。支持 Git 风格模式和否定规则。被忽略的父目录不会继续遍历，重新包含子项前需先重新包含父目录。`.git`、`.venv`、`node_modules`、`vendor` 和工具缓存始终跳过。显式指定单个文件会绕过忽略规则；目录遍历跳过符号链接。

默认缓存位于 `.fontguard-cache/`。只读挂载和 CI 可使用 `--no-cache`。缓存避免重复解析，但仍会计算文件内容哈希；CSS 引用的字体字节变化会使对应缓存失效。当前没有自动清理旧缓存的机制，可删除缓存目录回收空间。应在受信任的项目中保护缓存内容。

## 基线与审批

```sh
fontguard baseline create . --usage webfont
fontguard scan . --usage webfont --baseline .fontguard-baseline.json --fail-on review
```

基线中的匹配记录仍展示在报告中，但不触发所选阈值失败。新的哈希、身份、来源路径、用途、风险、许可或规则会产生新发现。扫描不完整时不能创建基线。请在 Git 中审核基线变化。

`fontguard allow` 在 `fontguard.lock` 中记录哈希、用途、理由和审批人。它记录组织声明，不验证采购事实。匹配的审批将风险调整为 `LOW`，但不能覆盖明确的字体或许可禁用规则。扫描时将 lock 文件放在扫描根目录；记录审批时可以用 `--lock` 指定位置。

## CI 集成与 Docker

```yaml
- name: Scan fonts
  run: fontguard scan . --usage webfont --fail-on high --format sarif --output fontguard.sarif --no-cache
- name: Upload SARIF
  if: always()
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: fontguard.sarif
```

参见[完整工作流示例](examples/github-actions.yml)。上传 SARIF 需要 `security-events: write` 和可用的 GitHub Code Scanning 功能。`.github/actions/fontguard` 中的组合 action 从检出的源码安装工具。GitLab/Jenkins 可执行相同 CLI 并保存 JSON/SARIF，由退出码控制任务状态。

`--git-diff` 选择相对 HEAD 的暂存区、工作区变化以及未跟踪文件。指定基准引用时，使用其与 HEAD 的共同祖先，并包括工作区和未跟踪变化；CI 需提前获取该引用。已删除的文件不会扫描。只修改字体文件不会重新扫描未改动的 CSS；策略、数据库、审批变化后，以及需要重新评估全部引用时，应执行完整扫描。

`.pre-commit-hooks.yaml` 的 hook ID 为 `fontguard`，会完整扫描并读取本地策略。使用发布仓库时应固定到已审核的版本。

尚未向镜像仓库发布 Docker 镜像。可自行构建：

```sh
docker build -t fontguard-local .
docker run --rm -v "$PWD:/workspace:ro" fontguard-local scan /workspace --usage webfont --no-cache
```

## 字体数据库

社区 YAML 数据位于 `data/fonts`、`data/licenses` 和 `data/vendors`，会打包进 wheel。

**2,052 条字体家族记录**由 2,020 个经核查的 Google Fonts 家族、单独维护的思源黑体，以及 31 个 Windows 分发字体家族组成。Noto Sans 的既有记录由官方目录补充，没有重复计数。导入的 Google Fonts 家族分别核对了自己的授权文件和元数据，保留固定上游提交 URL 及来源哈希。11 个无法验证或已退役的上游条目被明确排除。

中文字体示例包括 Noto Sans/Serif SC/TC、龙藏体（Long Cang）、马善政毛笔体（Ma Shan Zheng）、站酷系列，以及微软雅黑、宋体、黑体、楷体、等线等 Windows 字体别名。

识别先匹配精确名称，再尝试保留地区后缀的样式规范化，最后尝试通用规范化回退。有歧义的键不会用于回退，因此 Noto Sans、Noto Sans SC 和 Noto Sans TC 在身份、策略、去重和基线中保持区分。有歧义的导入别名会被省略并记录。

`--database` 可以指定完整的自定义数据库。校验覆盖结构、ID、精确别名冲突、许可/分发方引用、来源和哈希，不会访问 URL。导入命令、授权范围、排除项及二进制哈希详见[数据库来源说明](docs/font-database.zh-CN.md)。

## 开发与贡献

```sh
python -m pip install -e '.[dev]'
pytest
ruff check .
ruff format --check .
mypy
fontguard database validate
python -m build
```

参见[贡献指南](CONTRIBUTING.zh-CN.md)、[架构与扩展](docs/architecture.zh-CN.md)和[安全说明](SECURITY.zh-CN.md)。插件可通过 Python API 注册，也可安装入口点并用 `--plugins` 启用。

已完成 Windows 本机 72 项测试及 Ubuntu 服务器 72 项禁网容器测试，另完成 9 类真实文件验收。Windows/macOS/Linux × Python 3.11–3.13 和 Docker 共 [10 个 GitHub CI 任务全部通过](https://github.com/hengweiyv/FontGuard/actions/runs/36964651723)。详见[本机验证记录](docs/verification.zh-CN.md)及[服务器验证记录](docs/server-verification.zh-CN.md)。本次服务器测试资源已按要求清理；复现需重新准备测试环境。

## 许可证

原创代码与数据库记录采用 **Apache-2.0**，其明确的专利授权适合企业和社区工具。第三方字体继续遵循各自许可。

**PyMuPDF/MuPDF 采用 AGPL 或 Artifex 商业许可**，其条件适用于包含 PDF 功能的依赖组合和 Docker 镜像。FontGuard 的 Apache-2.0 许可不会覆盖依赖的许可义务。参见 [NOTICE](NOTICE)、[Apache 许可证](LICENSE)及 [PyMuPDF 许可说明](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright)。许可证原文保留英文。

## 使用范围说明

FontGuard 是字体授权合规辅助工具。报告不是法律意见，也不构成侵权认定。检测、数据库事实和用途声明可能不完整，商业字体也可能已获得授权。请核查实际字体来源、许可原文、合同范围和条件。

## 文档导航

| 文档 | 简体中文 | English |
| --- | --- | --- |
| 项目介绍与使用 | 本页 | [README](README.en.md) |
| 贡献指南 | [贡献指南](CONTRIBUTING.zh-CN.md) | [Contributing](CONTRIBUTING.md) |
| 安全说明 | [安全说明](SECURITY.zh-CN.md) | [Security](SECURITY.md) |
| 更新记录 | [更新记录](CHANGELOG.zh-CN.md) | [Changelog](CHANGELOG.md) |
| 架构与扩展 | [架构说明](docs/architecture.zh-CN.md) | [Architecture](docs/architecture.md) |
| 数据库来源 | [来源说明](docs/font-database.zh-CN.md) | [Database provenance](docs/font-database.md) |
| 本机验证 | [本机验证](docs/verification.zh-CN.md) | [Local verification](docs/verification.md) |
| 服务器验证 | [服务器验证](docs/server-verification.zh-CN.md) | [Server verification](docs/server-verification.md) |
| SARIF schema 来源 | [来源说明](tests/schemas/README.zh-CN.md) | [Schema provenance](tests/schemas/README.md) |
