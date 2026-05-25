# Sci Reader Skill

面向学术阅读场景的 opencode skill。它可以把本地 PDF 论文通过 MinerU 转换为 Markdown，再生成适合收入 Obsidian 的中文文献阅读笔记；也可以处理 ScienceDirect / Elsevier 期刊 issue 导出的 citation 文件，按原始 issue 顺序翻译文章标题与摘要，并生成期刊总结。

## 功能概览

### 1. PDF 论文阅读笔记

适用于用户提供本地 PDF 论文并要求阅读、总结、分析或写文献笔记的场景。

工作流：

1. 使用 MinerU API v4 将本地 PDF 转换为 Markdown。
2. 阅读转换后的论文内容，重点关注摘要、引言、方法、结果、讨论、局限和结论。
3. 按 `文献阅读笔记-模板.md` 生成 Obsidian-ready Markdown 笔记。
4. 保留论文中的关键证据，例如数据集、模型、指标、数值结果、图表编号、实验设置等。
5. 如果 MinerU 转换结果缺失图表、表格、公式、参考文献或补充材料，会在笔记中说明限制。

默认文献笔记结构包括：

```markdown
---
英文标题:
中文标题:
tags:
发表年份:
阅读日期:
---
> [!info] 中文摘要
> ...

## 1. 总结

## 2. 研究问题
- **研究背景：**
- **核心问题：**

## 3. 方法与思路
- **主要方法：**
- **关键概念 / 模型：** [[ ]]
- **基本逻辑：**

## 4. 主要结论

## 5. 综合评价
- **优点：**
- **局限：**
```

### 2. ScienceDirect / Elsevier issue 摘要翻译

适用于从 ScienceDirect / Elsevier 导出的单期期刊 citation `.txt` 文件。导出文件通常包含多篇文章的作者、英文标题、期刊信息、年份、DOI、链接、`Abstract:` 和 `Keywords:`。

工作流：

1. 使用 `scripts/parse_sciencedirect_export.py` 解析导出文件。
2. 保留原始导出顺序，默认不按标题、DOI、主题或字母排序。
3. 将每篇文章的英文标题和摘要翻译为学术中文。
4. 对缺失摘要的文章明确标注 `摘要：未在导出文件中提供摘要。`
5. 在长 issue 中分批处理，但最终会检查翻译条目数是否与解析记录数一致。

每篇文章默认输出格式：

```markdown
中文标题：<中文标题>
英文标题：<原始英文标题>
摘要：<中文摘要>
```

### 3. 期刊 issue 总结

当用户需要“本期总结”“issue overview”“趋势综合”或“最终可放入 Obsidian 的期刊总结文档”时，skill 会使用 `期刊总结-模板.md`。

期刊总结基于已翻译的标题和摘要生成，不会假装读过全文。默认包含：

- 本期总览
- 本期速览表
- 核心应用场景
- 主要方法底座
- 本期关键词
- 高频热词与趋势
- 核心研究对象
- 核心研究方法 / 模型
- 新颖切入点
- 完整的文章标题与摘要翻译列表

模板使用 Obsidian callout 和 Markdown 表格，最终输出会替换所有 `{{...}}` 占位符。

## 文件说明

```text
.
├── SKILL.md                         # opencode skill 主说明文件
├── agents/
│   └── openai.yaml                  # agent/skill 元信息
├── scripts/
│   ├── mineru_to_markdown.py        # 调用 MinerU API v4 将 PDF 转 Markdown
│   └── parse_sciencedirect_export.py# 解析 ScienceDirect/Elsevier citation 导出文件
├── 文献阅读笔记-模板.md              # 单篇论文 Obsidian 阅读笔记模板
└── 期刊总结-模板.md                  # 期刊 issue 总结模板
```

## 安装 / 使用

将本仓库作为 opencode skill 路径使用。具体路径取决于你的 opencode 配置，例如可以放在：

```text
~/.config/opencode/skills/sci-reader/
```

或在 `opencode.json` 中配置自定义 skill 路径。

修改或新增 skill 文件后，需要重启 opencode 才会生效。

## MinerU 配置

PDF 转 Markdown 依赖 MinerU API。

必需环境变量：

```bash
export MINERU_API_KEY="你的 MinerU API Token"
```

可选环境变量：

```bash
export MINERU_API_BASE_URL="https://mineru.net/api/v4"
export MINERU_POLL_INTERVAL="5"
export MINERU_TIMEOUT="900"
export MINERU_MODEL_VERSION="vlm"
```

## 脚本用法

### PDF 转 Markdown

```bash
python scripts/mineru_to_markdown.py paper.pdf --out outputs/paper_name
```

脚本会：

1. 请求 MinerU signed upload URL。
2. 使用 `PUT` 上传 PDF。
3. 轮询 batch 解析结果。
4. 下载 `full_zip_url`。
5. 解压并返回生成的 Markdown 路径。

### 解析 ScienceDirect / Elsevier 导出文件

输出 JSON：

```bash
python scripts/parse_sciencedirect_export.py issue-export.txt --format json
```

输出 Markdown：

```bash
python scripts/parse_sciencedirect_export.py issue-export.txt --format markdown --out issue-records.md
```

解析器会尽量读取 `utf-8-sig`、`utf-8`、`cp1252`、`gb18030` 编码，并保留原始记录顺序。

## Obsidian 约定

最终 Markdown 文档面向 Obsidian 收录，因此会尽量保留和使用：

- YAML frontmatter
- Callout，例如 `> [!info]`、`> [!abstract]`、`> [!tip]`
- Wiki link，例如 `[[Transformer]]`、`[[因果推断]]`
- Markdown 表格
- 清晰的中文标题层级

skill 会避免在最终文档中留下模板占位符或示例文本。

## 注意事项

- PDF 阅读质量取决于 MinerU 转换结果。
- issue 总结只基于导出的标题和摘要，不等同于全文综述。
- bibliographic metadata 缺失时会标注为 `未在正文中明确找到`，不会编造。
- ScienceDirect issue 默认保留导出顺序，除非用户明确要求重新排序。
