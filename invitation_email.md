# Invitation Email to Research Colleagues

## Subject Line Options

- **Option A:** Join ResearchTwin — your AI-powered research digital twin
- **Option B:** Invitation: Create your research digital twin on ResearchTwin
- **Option C:** Your research, unified — join the ResearchTwin network

---

## Email Body

Dear [Name],

I'm writing to invite you to join **ResearchTwin** — an open-source platform I've been building that turns your publications, datasets, and code repositories into a unified, interactive research profile.

### What it does

ResearchTwin pulls your work from Semantic Scholar, Google Scholar, GitHub, and Figshare, then:

- Computes your **S-Index** — a transparent metric combining Quality (FAIR compliance), Impact (field-normalized reuse), and Collaboration (team breadth) across all your research outputs
- Generates an interactive **knowledge graph** visualizing your papers, repos, and datasets
- Provides a conversational **AI interface** so colleagues (and AI agents) can explore your work
- Exposes a machine-readable **discovery API** for emerging agent-to-agent research workflows

### Getting started (60 seconds)

1. Go to **https://researchtwin.net/join.html**
2. Enter your name, email, and any research IDs you have (Semantic Scholar, Google Scholar, GitHub)
3. Your digital twin is live immediately

That's it. You can always add or update your research identifiers later.

### Why I think this matters

The exponential growth of research outputs has created a real discovery bottleneck. Static PDFs and siloed repositories make it hard for both humans and AI to find and build on existing work. ResearchTwin is my attempt at a solution — a federated network where every researcher's full body of work is discoverable, measurable, and conversational.

The S-Index in particular addresses a gap I've noticed: traditional metrics like h-index only capture publication impact. They miss datasets, code, and other shared artifacts that are increasingly central to reproducible science. The S-Index brings these into one transparent score.

### Embed your S-Index

Once your twin is live, you can embed a live S-Index widget on your lab website or Google Sites page:

```html
<iframe src="https://researchtwin.net/embed.html?slug=YOUR-SLUG"
  width="440" height="180"
  style="border:none; border-radius:12px;"
  loading="lazy"></iframe>
```

### Open source

ResearchTwin is MIT-licensed and open source. The platform code, S-Index specification, and reference implementation are all on GitHub:

- Platform: https://github.com/martinfrasch/researchtwin
- S-Index spec: https://github.com/martinfrasch/s-index

The formal description of the S-Index methodology and the federated architecture is available as a whitepaper (preprint forthcoming on arXiv).

If you have questions, feedback, or ideas for collaboration, just reply to this email. I'd especially value your thoughts on the S-Index formula and whether the FAIR-gate approach makes sense for your field.

Best regards,

**Martin G. Frasch**
Health Stream Analytics, LLC
University of Washington, Seattle
https://researchtwin.net
martin@researchtwin.net

---

## Usage Notes

- Replace `[Name]` with the recipient's first name or "Colleagues" for a group email
- The tone is collegial and informational, not salesy
- Customize the "Why I think this matters" paragraph for different audiences (e.g., emphasize datasets for data-heavy fields, code for computational researchers)
- For bulk sends, consider using BCC to protect recipient privacy
