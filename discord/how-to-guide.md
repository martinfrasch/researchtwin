# ResearchTwin Discord Guide

Copy each section below into its own message in a `#how-to` or `#getting-started` channel.

---

## MESSAGE 1: Welcome

**Welcome to ResearchTwin**

ResearchTwin is a digital twin of a researcher's body of work — publications, code, datasets, and impact metrics — powered by live data and AI.

Use slash commands to explore research profiles interactively.

**Available Commands**
`/research` — Ask a question about a researcher's work
`/sindex` — Check a researcher's real-time QIC-Index (impact score)

---

## MESSAGE 2: /research command

**How to use `/research`**

Ask any question about a researcher's publications, code, datasets, or expertise.

**Usage**
```
/research query: <your question> slug: <researcher-id>
```

**Examples**
```
/research query: What are the main research areas? slug: martin-frasch
/research query: Which papers have the most citations? slug: martin-frasch
/research query: What code repositories are available? slug: martin-frasch
/research query: How does HRV relate to fetal brain development? slug: martin-frasch
/research query: What datasets are publicly available? slug: martin-frasch
```

**Tips**
- Be specific — "What methods were used for ASD detection?" works better than "Tell me about ASD"
- Ask about connections — "How do the GitHub repos relate to the published papers?"
- Ask for summaries — "Give me a 3-sentence overview of this researcher's impact"
- You can ask about the QIC-Index — "Explain the S-Index score and what drives it"

---

## MESSAGE 3: /sindex command

**How to use `/sindex`**

Get a real-time impact score based on the QIC-Index framework (Quality x Impact x Collaboration).

**Usage**
```
/sindex slug: <researcher-id>
```

**What the score measures**
- **Quality (Q)** — FAIR data principles: Findability, Accessibility, Interoperability, Reusability
- **Impact (I)** — Downloads, citations, and reuse events
- **Collaboration (C)** — Author and institutional breadth

The score aggregates across all shared datasets and code repositories.

---

## MESSAGE 4: Example queries to try

**Not sure what to ask? Start here**

**Overview questions**
> /research query: Give me a summary of this researcher's work slug: martin-frasch
> /research query: What are the top 5 most cited papers? slug: martin-frasch

**Technical deep-dives**
> /research query: What machine learning methods are used in the ASD project? slug: martin-frasch
> /research query: How is heart rate variability analyzed in the code repos? slug: martin-frasch

**Impact and metrics**
> /research query: What drives the S-Index score? slug: martin-frasch
> /research query: How do the datasets score on FAIR principles? slug: martin-frasch
> /sindex slug: martin-frasch

**Cross-source questions**
> /research query: Which papers have corresponding code or data repositories? slug: martin-frasch
> /research query: What is the relationship between the Figshare datasets and the publications? slug: martin-frasch

---

## MESSAGE 5: How it works (optional, for a #about channel)

**How ResearchTwin Works**

ResearchTwin pulls live data from three sources:

**Semantic Scholar** — Publications, citations, h-index
**GitHub** — Code repositories, languages, activity
**Figshare** — Datasets, downloads, metadata

This data feeds into the **QIC-Index** calculator, which scores each shared data object on Quality (FAIR principles), Impact (reuse), and Collaboration (team breadth).

When you ask a question via `/research`, all this context is assembled and sent to an AI that answers based solely on the researcher's actual data — no hallucinated papers or made-up metrics.

The QIC-Index framework is described at: https://github.com/martinfrasch/s-index

---

## MESSAGE 6: Available researchers

**Currently Available Researchers**

| Slug | Researcher | Areas |
|------|-----------|-------|
| `martin-frasch` | Martin Frasch, MD PhD | Perinatal neuroscience, HRV, AI in medicine |

More researchers will be added over time. To request a profile, reach out to the server admin.
