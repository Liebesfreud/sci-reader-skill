---
name: sci-reader
description: Read academic PDF papers by converting them to Markdown with the MinerU API, then produce a structured Markdown literature-reading report. Use when the user asks to read, summarize, analyze, review, or report on scholarly papers from PDF files.
metadata:
  short-description: Read papers via MinerU Markdown conversion
---

# Sci Reader

Use this skill to turn a PDF paper into Markdown with MinerU, read the converted content, and write a focused Markdown report.

## Core Workflow

1. **Confirm input**: Identify the PDF path and the desired report language. Default to the user's language.
2. **Convert PDF**: Run `scripts/mineru_to_markdown.py` with the PDF path and an output directory.
3. **Read Markdown**: Open the generated `.md`; if it is long, inspect headings first, then read the abstract, introduction, methods, results, discussion, limitations, and conclusion.
4. **Write report**: Create a Markdown report next to the converted paper unless the user specifies another path.
5. **Mention gaps**: If conversion omits figures, tables, formulas, references, or supplemental details, state that limitation in the report.

## MinerU Conversion

Use the bundled script when a PDF needs conversion:

```bash
python scripts/mineru_to_markdown.py paper.pdf --out outputs/paper_name
```

Required environment variable:

- `MINERU_API_KEY`: MinerU API token.

Optional environment variables:

- `MINERU_API_BASE_URL`: Defaults to `https://mineru.net/api/v4`.
- `MINERU_POLL_INTERVAL`: Polling interval in seconds; defaults to `5`.
- `MINERU_TIMEOUT`: Maximum polling time in seconds; defaults to `900`.

If the API workflow changes, prefer updating `scripts/mineru_to_markdown.py` rather than embedding ad-hoc API calls in the answer.

## Report Format

Produce a concise, evidence-grounded Markdown report with this structure by default:

```markdown
# 文献阅读报告：<论文标题>

## 1. 基本信息
- 题目：
- 作者：
- 年份 / 期刊或会议：
- DOI / 链接：
- 研究领域：

## 2. 摘要

## 3. 研究问题与动机

## 4. 方法概述

## 5. 关键发现

## 6. 重要图表与证据

## 7. 创新点与贡献

## 8. 局限性

## 9. 可复用思路

## 10. 后续阅读问题
```

Adapt headings when the user requests a different style, such as a reviewer report, lab meeting note, replication plan, or bullet-only summary.

## Reading Rules

- Do not invent bibliographic metadata; mark missing fields as `未在正文中明确找到`.
- Preserve important technical terms, model names, datasets, metrics, equations, and experimental settings.
- Distinguish the paper's claims from your interpretation.
- Prefer specific findings over generic summaries.
- If the converted Markdown is noisy, say so and base conclusions only on readable sections.

## Output Rules

- Save the final report as Markdown when the user asks for a file or when a PDF was converted.
- Use clear section headings and compact bullets.
- Include the converted Markdown path and report path in the final response.

