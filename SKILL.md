---
name: sci-reader
description: Read academic PDF papers by converting them to Markdown with the MinerU API, then produce an Obsidian-ready Markdown literature reading note using the bundled template. Also translate ScienceDirect/Elsevier exported issue citation files containing article titles and abstracts into Chinese in page or issue order, and optionally produce an Obsidian-ready journal issue summary. Use when the user asks to read, summarize, analyze, review, report on scholarly papers from PDF files, or translate/summarize a journal issue's exported titles and abstracts.
metadata:
  short-description: Read papers via MinerU Markdown conversion
---

# Sci Reader

Use this skill for two literature workflows:

1. Turn a PDF paper into Markdown with MinerU, read the converted content, and write an Obsidian-ready literature reading note using `文献阅读笔记-模板.md`.
2. Translate ScienceDirect/Elsevier exported issue citation files containing article titles and abstracts into Chinese, preserving the original page or issue order, and optionally write an Obsidian-ready journal issue summary using `期刊总结-模板.md`.

## Core Workflow

1. **Confirm input**: Identify the PDF path and the desired note language. Default to the user's language.
2. **Convert PDF**: Run `scripts/mineru_to_markdown.py` with the PDF path and an output directory.
3. **Read Markdown**: Open the generated `.md`; if it is long, inspect headings first, then read the abstract, introduction, methods, results, discussion, limitations, and conclusion.
4. **Write note**: Create an Obsidian-ready Markdown reading note next to the converted paper unless the user specifies another path. Use the structure in `文献阅读笔记-模板.md` by default.
5. **Mention gaps**: If conversion omits figures, tables, formulas, references, or supplemental details, state that limitation in the note.

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
4. **Translate each article**: For every record with a title and abstract, output exactly this structure in the translated article list:

```markdown
中文标题：<faithful Chinese title>
英文标题：<original English title>
摘要：<Chinese translation of the abstract>
```

5. **Translation style**: Translate into fluent academic Chinese. Preserve technical terms, model names, dataset names, abbreviations, formulas, percentages, metrics, proper nouns, and named methods. Prefer natural Chinese syntax over literal word order.
6. **Completeness checks**: Do not omit articles. If an abstract is missing, write `摘要：未在导出文件中提供摘要。` If a title is missing, mark the title field as missing instead of inventing it.
7. **Output files**: When translating a full issue or many articles, save a Markdown file next to the input or in the user-specified output path. If the user asks for an issue summary, or asks for a final Obsidian-ready issue document, use `期刊总结-模板.md`: fill the trend/summary sections from the translated titles and abstracts, then paste the complete translated article list under the final placeholder section.
8. **Final response**: Include the source file path and every output path in the final response.

For long issues, work in batches but keep a running article count and append results in the parsed order. Before finalizing, compare the number of translated entries with the number of parsed records.

## Literature Reading Note Template

Use `文献阅读笔记-模板.md` as the default final document structure for single-paper reading notes. The finished Markdown is intended for Obsidian, so preserve YAML frontmatter, Obsidian callouts, and wiki-link syntax where appropriate.

Default structure:

```markdown
---
英文标题:
中文标题:
tags:
发表年份:
阅读日期:
---
> [!info] 中文摘要
> 这是一句摘要。

## 1. 总结
这篇文章研究了什么问题？用了什么方法？得出了什么结论？

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

Fill this template as follows:

- `英文标题`: original paper title. Do not invent it; if missing, write `未在正文中明确找到`.
- `中文标题`: faithful Chinese translation of the title.
- `tags`: concise Obsidian tags such as `[论文, 领域名, 方法名]` or another valid style the user prefers. Avoid excessive tags.
- `发表年份`: publication year if available; otherwise `未在正文中明确找到`.
- `阅读日期`: today's date in `YYYY-MM-DD` format unless the user specifies another date.
- `中文摘要` callout: write a compact Chinese abstract, usually 1-3 sentences, not a placeholder.
- `总结`: explain the research problem, method, and conclusion in a few coherent paragraphs.
- `研究问题`: fill both the background and core question with specific, evidence-grounded content.
- `方法与思路`: name concrete methods, models, datasets, variables, metrics, or experimental designs when available. Use Obsidian wiki links for key concepts or models only when they are likely to be reusable notes, e.g. `[[Transformer]]`, `[[Diffusion Model]]`, or `[[因果推断]]`.
- `主要结论`: list or explain the main findings with numbers, baselines, datasets, figures, or table references when available.
- `综合评价`: separate strengths from limitations. Include limitations stated by the paper and cautious limitations inferred from the readable evidence.

Adapt headings only when the user explicitly requests a different style, such as a reviewer report, lab meeting note, replication plan, or bullet-only summary.

## Journal Issue Summary Template

Use `期刊总结-模板.md` when the user provides a ScienceDirect/Elsevier issue export and asks for a journal issue summary, issue overview, trend synthesis, or Obsidian-ready final issue document. This summary is built from the translated article titles and abstracts, not from invented full-paper details.

Default structure:

```markdown
> [!abstract] 本期总览
> {{本期宏观判断：用1-2句话概括本期研究主线和演进方向}}

---

## 本期速览

| 维度 | 观察结论 |
|---|---|
| **核心应用场景** | {{列出3-5个主要应用领域}} |
| **主要方法底座** | {{列出3-5个核心方法/模型}} |
| **研究气质** | {{用一句话描述本期论文的整体研究取向}} |
| **本期关键词** | {{提炼5-8个高频关键词}} |

> [!tip] 一句话判断
> {{用一句话点出本期最值得关注的变化或趋势}}

---

## 1. 高频热词与趋势

### 1.1 核心研究对象

| 核心对象 | 热度 | 代表文章 | 趋势含义 |
|---|---:|---|---|
| **{{对象1}}** | 高/中/低 | {{列出2-3篇代表文章}} | {{一句话解释该对象为何突出}} |

### 1.2 核心研究方法 / 模型

| 方法簇 | 代表文章 | 方法角色 |
|---|---|---|
| **{{方法簇1}}** | {{列出2-3篇代表文章}} | {{一句话概括该方法的角色}} |

> [!note] 为什么这些主题在本期集中出现？
> {{解释本期主题聚类背后的学科趋势或现实驱动力}}

---

## 2. 新颖切入点

| 文章 | 新颖之处 | 可借鉴价值 |
|---|---|---|
| **{{文章1}}** | {{它新在哪里}} | {{对后续研究有什么启发}} |

> [!example] 本期最值得关注的研究信号
> {{用一句话提炼本期最有前瞻价值的跨文章共同信号}}

---

{{在此粘贴本期各文章的标题与摘要}}
```

Fill this template as follows:

- Preserve Obsidian callout syntax and Markdown tables.
- Replace every `{{...}}` placeholder with real content; do not leave template placeholders in final output.
- Base trend judgments only on the exported titles and abstracts. If the evidence is weak, state that the judgment is based on abstracts only.
- Representative articles should use the translated Chinese title where possible, with the English title retained in the article list below.
- Use `高/中/低` heat labels comparatively within the current issue, not as field-wide claims.
- Under the final section, paste the complete translated article list in the parsed order using the required per-article structure from the ScienceDirect workflow.
- Before finalizing, verify that the final pasted article list contains the same number of entries as the parsed records.

## Detail Expectations

- For a normal paper, fill the Obsidian reading note with enough detail to support later retrieval and reuse, usually 800-1,800 Chinese characters unless the user requests a shorter or longer note.
- Each analytical section should contain substantive content, not just copied abstract sentences or one-line fragments.
- Include concrete evidence from the paper whenever available: dataset names, sample sizes, model names, parameter settings, baselines, metrics, numeric results, figure/table numbers, and quoted terms.
- If the converted Markdown lacks enough detail for a section, say what is missing and explain what can still be inferred from the readable text.
- For issue summaries, synthesize cross-paper patterns from titles and abstracts while avoiding claims that would require full-text evidence.

## Reading Rules

- Do not invent bibliographic metadata; mark missing fields as `未在正文中明确找到`.
- Preserve important technical terms, model names, datasets, metrics, equations, and experimental settings.
- Distinguish the paper's claims from your interpretation.
- Prefer specific findings over generic summaries.
- If the converted Markdown is noisy, say so and base conclusions only on readable sections.

## Output Rules

- Save the final single-paper reading note as Markdown when the user asks for a file or when a PDF was converted.
- Save full-issue translations and issue summaries as Markdown when processing a complete issue export.
- The final Markdown documents are intended for Obsidian: preserve YAML frontmatter, callouts such as `> [!info]`, wiki links, tables, and clean Markdown formatting.
- Do not leave template placeholders such as `{{...}}` or sample text like `这是一句摘要。` in finished documents.
- Use clear section headings. Prefer the bundled templates unless the user explicitly asks for a different structure.
- Include the converted Markdown path, source export path, reading note path, translation path, and/or issue summary path in the final response as applicable.
