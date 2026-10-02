# 架构与扩展接口

**简体中文** | [English](architecture.md) | [返回首页](../README.md)

处理流程：

`Scanner → AnalyzerRegistry → 原始 AnalysisResult → FontIdentityEngine → 许可引擎 → 策略引擎 → 审批 → 基线 → 报告器`。

## 数据与身份识别

接口数据模型使用 `core/models.py` 中的 Pydantic 模型。分析器保留来源位置和原始元数据。身份识别优先使用 SHA256，再尝试 PostScript 名称、完整名称、家族名与别名。

名称处理可以去除样式词、PDF 子集前缀和文件扩展名。先匹配精确别名，再匹配保留地区标记的样式规范化名称，最后尝试通用规范化回退。通用回退可能移除地区词，但有歧义的键不会匹配。仅显式映射繁体 `體` 字形，不进行广泛的中文转换或模糊匹配。

不同地区的家族在身份、策略和基线中保持独立。名称匹配不能证明来源；字体 name 表中的许可文本也不会仅因被读取就成为可信授权数据。

YAML 数据库记录事实、各用途许可和来源。风险在扫描时计算，策略或数据库变化会重新评估缓存中的原始观察记录。扫描和数据库校验均不联网。

## 分析器插件

实现无状态、线程安全的 `Analyzer`：

```python
from pathlib import Path
from fontguard.analyzers.base import Analyzer
from fontguard.core.models import AnalysisResult


class SubtitleAnalyzer(Analyzer):
    extensions = frozenset({".ass"})

    def analyze(self, path: Path) -> AnalysisResult:
        # 解析字幕，返回包含 Evidence 的 DetectedFont 观察记录。
        return AnalysisResult()
```

Python API 可以调用 `registry.register(SubtitleAnalyzer())` 注册，也可以将工厂发布到 `fontguard.analyzers` Python 入口点组。CLI 仅在使用 `--plugins` 时加载已安装插件。多个分析器匹配同一文件时，最先注册的分析器优先；自定义注册表可替换默认分析器。特殊文件可以覆盖 `supports`。

插件不得发起远程请求，并应限制解析器资源使用。

## 调度与缓存

调度前按扩展名过滤文件，并剪枝被忽略的目录。线程以有界批次并行处理独立文件。由于 PyMuPDF 不是线程安全的，PDF 解析保留在调用线程执行。

缓存键包含路径、mtime、大小、SHA256、分析器名称和版本；CSS 的缓存键还包含其本地字体引用的哈希。未变化的文件仍会计算哈希，缓存节省的是解析工作，而非所有磁盘 I/O。`--no-cache` 不创建缓存目录。缓存格式或解析逻辑变化需更新版本。当前没有自动淘汰机制，可删除 `.fontguard-cache` 回收旧版本缓存。

## 基线与审批

指纹包含相对来源路径、字体哈希或数据库身份/名称、规则、风险、用途和许可。基线保留报告中的发现，但将匹配指纹排除在 CI 失败判断之外。风险、规则、用途、哈希或身份变化会产生新发现。

审批按实际哈希和用途限定范围，不按名称生效；明确的组织禁用规则优先。这些记录是组织声明，不构成法律证据。
