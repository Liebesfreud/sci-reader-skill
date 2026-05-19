---
name: sci-reader
description: Read academic PDF papers by converting them to Markdown with the MinerU API, then produce a structured, detailed Markdown literature-reading report. Also translate ScienceDirect/Elsevier exported issue citation files containing article titles and abstracts into Chinese in page or issue order. Use when the user asks to read, summarize, analyze, review, report on scholarly papers from PDF files, or translate a journal issue's exported titles and abstracts.
metadata:
  short-description: Read papers via MinerU Markdown conversion
---

# Sci Reader

Use this skill for two literature workflows:

1. Turn a PDF paper into Markdown with MinerU, read the converted content, and write a detailed Markdown literature-reading report.
2. Translate ScienceDirect/Elsevier exported issue citation files containing article titles and abstracts into Chinese, preserving the original page or issue order.

## Core Workflow

1. **Confirm input**: Identify the PDF path and the desired report language. Default to the user's language.
2. **Convert PDF**: Run `scripts/mineru_to_markdown.py` with the PDF path and an output directory.
3. **Read Markdown**: Open the generated `.md`; if it is long, inspect headings first, then read the abstract, introduction, methods, results, discussion, limitations, and conclusion.
4. **Write report**: Create a Markdown report next to the converted paper unless the user specifies another path.
5. **Mention gaps**: If conversion omits figures, tables, formulas, references, or supplemental details, state that limitation in the report.

## MinerU Conversion

Use the bundled script when a local PDF needs conversion:

```bash
python scripts/mineru_to_markdown.py paper.pdf --out outputs/paper_name
```

The script follows MinerU v4's local-file flow: request signed upload URLs from `/api/v4/file-urls/batch`, upload the PDF with `PUT`, poll `/api/v4/extract-results/batch/{batch_id}`, download `full_zip_url`, then extract the Markdown file.

Required environment variable:

- `MINERU_API_KEY`: MinerU API token.

Optional environment variables:

- `MINERU_API_BASE_URL`: Defaults to `https://mineru.net/api/v4`.
- `MINERU_POLL_INTERVAL`: Polling interval in seconds; defaults to `5`.
- `MINERU_TIMEOUT`: Maximum polling time in seconds; defaults to `900`.
- `MINERU_MODEL_VERSION`: Defaults to `vlm`; use another MinerU-supported model when needed.

If the API workflow changes, prefer updating `scripts/mineru_to_markdown.py` rather than embedding ad-hoc API calls in the answer.

## ScienceDirect Issue Translation

Use this workflow when the user provides a ScienceDirect/Elsevier citation export for one journal issue, usually a `.txt` file containing repeated records with authors, English title, journal, volume, year, DOI/link, `Abstract:`, and `Keywords:`.

1. **Parse records first**: Run `scripts/parse_sciencedirect_export.py` on the export file to inspect the number and order of articles.
2. **Preserve order**: Keep the original export order as the default article order. ScienceDirect issue exports are normally already ordered by issue table of contents, page range, or article locator. Do not sort alphabetically, by DOI, by title, or by topic.
3. **Use page data carefully**: If the export includes explicit page ranges, use the first page only to verify or restore page order. If it uses article numbers instead of pages, treat those numbers as locators and keep the original order unless the user explicitly asks for numeric sorting.
4. **Translate each article**: For every record with a title and abstract, output exactly this structure:

```markdown
中文标题：<faithful Chinese title>
英文标题：<original English title>
摘要：<Chinese translation of the abstract>
```

5. **Translation style**: Translate into fluent academic Chinese. Preserve technical terms, model names, dataset names, abbreviations, formulas, percentages, metrics, proper nouns, and named methods. Prefer natural Chinese syntax over literal word order.
6. **Completeness checks**: Do not omit articles. If an abstract is missing, write `摘要：未在导出文件中提供摘要。` If a title is missing, mark the title field as missing instead of inventing it.
7. **Output file**: When translating a full issue or many articles, save a Markdown file next to the input or in the user-specified output path. Include the source file path and output path in the final response.

For long issues, work in batches but keep a running article count and append results in the parsed order. Before finalizing, compare the number of translated entries with the number of parsed records.

## Report Format

Produce a detailed, evidence-grounded Markdown report with this structure by default. Prefer explanatory paragraphs over bullet lists. Use bullets only when they improve scanability, such as listing bibliographic metadata, datasets, metrics, limitations, or follow-up questions.

```markdown
# 文献阅读报告：<论文标题>

## 1. 基本信息
| 字段 | 内容 |
| --- | --- |
| 题目 |  |
| 作者 |  |
| 年份 / 期刊或会议 |  |
| DOI / 链接 |  |
| 研究领域 |  |

## 2. 摘要
用 2-4 个自然段说明论文的研究对象、核心问题、方法路线、主要结论和适用边界。不要只改写摘要原文，要把论文试图解决什么问题讲清楚。

## 3. 研究问题与动机
用段落解释研究背景、已有工作的不足、作者为什么认为这个问题重要，以及论文的研究问题如何被定义。必要时补充关键术语。

## 4. 方法概述
用段落描述方法或实验设计的完整链条，包括数据来源、模型/算法/理论框架、变量或指标、实验设置、对照方案和评价方式。复杂方法可以加入少量列表，但列表项必须有解释。

## 5. 关键发现
用段落展开每个主要发现：先说明发现是什么，再说明证据来自哪里，最后说明它对研究问题意味着什么。保留具体数值、指标、对比对象和实验条件。

## 6. 重要图表与证据
按图表或实验结果解释证据。说明每个重要图表回答了什么问题、展示了什么趋势或差异、以及是否存在需要谨慎解读的地方。

## 7. 创新点与贡献
用段落区分作者明确声称的贡献与你的解读。说明这些贡献相对于已有工作的增量在哪里，而不只是罗列“提出了方法、做了实验”。

## 8. 局限性
说明论文自身承认的局限，以及从方法、数据、实验外推、评价指标或论证链条中可以推断出的潜在局限。不要夸大论文没有支持的批评。

## 9. 可复用思路
说明这篇论文中哪些问题定义、数据处理、实验设计、模型结构、指标选择或写作结构可以迁移到其他研究中，并解释如何迁移。

## 10. 后续阅读问题
列出 3-6 个值得继续追问的问题，每个问题后补一句为什么它重要。
```

Adapt headings when the user requests a different style, such as a reviewer report, lab meeting note, replication plan, or bullet-only summary.

## Detail Expectations

- For a normal paper, aim for a report that is long enough to support later discussion or reuse, usually 1,500-3,000 Chinese characters unless the user requests a shorter or longer report.
- Each analytical section should contain at least one substantive paragraph. Avoid sections that contain only a heading and several short bullet fragments.
- Do not create many one-line bullets. When using bullets, make each bullet self-contained and explanatory.
- Include concrete evidence from the paper whenever available: dataset names, sample sizes, model names, parameter settings, baselines, metrics, numeric results, figure/table numbers, and quoted terms.
- If the converted Markdown lacks enough detail for a section, say what is missing and explain what can still be inferred from the readable text.

## Reading Rules

- Do not invent bibliographic metadata; mark missing fields as `未在正文中明确找到`.
- Preserve important technical terms, model names, datasets, metrics, equations, and experimental settings.
- Distinguish the paper's claims from your interpretation.
- Prefer specific findings over generic summaries.
- If the converted Markdown is noisy, say so and base conclusions only on readable sections.

## Output Rules

- Save the final report as Markdown when the user asks for a file or when a PDF was converted.
- Use clear section headings. Prefer paragraphs and tables over compact bullets unless the user explicitly asks for a bullet-style report.
- Include the converted Markdown path and report path in the final response.
