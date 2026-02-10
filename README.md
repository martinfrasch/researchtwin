# ResearchTwin: Federated Agentic Web of Research Knowledge

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

ResearchTwin is an open-source, federated platform that transforms a researcher's publications, datasets, and code repositories into a conversational **Digital Twin**. Inspired by biological Bimodal Glial-Neural Optimization (BGNO), it enables a dual-discovery pathway where both humans and AI agents collaborate to accelerate scientific discovery.

---

## 🚀 Project Vision

The exponential growth of scientific outputs has created a "discovery bottleneck." Traditional static PDFs and siloed repositories limit knowledge synthesis and reuse. ResearchTwin addresses this by:

- Integrating multi-modal research artifacts from **Semantic Scholar**, **GitHub**, and **Figshare**.
- Implementing a real-time **S-index** metric that captures impact across citations, code utility, and data reuse.
- Providing a conversational chatbot interface for interactive exploration of research.
- Enabling a **federated, Discord-like architecture** that supports local nodes, hubs, and hosted edges.
- Fostering an **agentic web of knowledge** where AI agents autonomously discover inter-lab synergies.

---

## 🏗️ Architecture Overview

![BGNO Architecture](docs/bgno_architecture.png)

### Key Components

- **Multi-Modal Connector Layer:**  
  Pulls data on-demand from Semantic Scholar (publications), GitHub (code), and Figshare (datasets).

- **Glial Layer:**  
  Handles caching, rate limiting, and context preparation to optimize data flow and cost.

- **Neural Layer:**  
  Uses Retrieval-Augmented Generation (RAG) with RouteLLM API to synthesize answers from aggregated context.

- **Conversational Chatbot / Digital Twin:**  
  Exposes the integrated context via a chat interface on the web and Discord.

### Federated Network Tiers

| Tier          | Description                                                                                  |
|---------------|----------------------------------------------------------------------------------------------|
| **Local Nodes**  | Individual researchers or labs hosting lightweight instances with their own data connectors. |
| **Hubs**         | Aggregators federating multiple local nodes for inter-lab knowledge sharing.                |
| **Hosted Edges** | Cloud-hosted services providing advanced analytics, global discovery indices, and premium features. |

---

## ⚙️ Getting Started

### Prerequisites

- Docker & Docker Compose
- API keys for:
  - Semantic Scholar
  - GitHub (optional but recommended)
  - Figshare (optional)
  - Discord Bot Token (for Discord integration)

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/your-org/researchtwin.git
   cd researchtwin
   ```

2. Create a `.env` file with your API keys:

   ```env
   SEMANTIC_SCHOLAR_API_KEY=your_ss_key
   GITHUB_TOKEN=your_github_token
   FIGSHARE_TOKEN=your_figshare_token
   DISCORD_BOT_TOKEN=your_discord_bot_token
   ```

3. Build and start the services:

   ```bash
   docker-compose up -d --build
   ```

4. Access the chatbot widget via your configured domain or localhost.

5. Invite the Discord bot to your server and use `/research` and `/sindex` commands.

---

## 📂 Repository Structure

```
researchtwin/
├── backend/                # FastAPI backend service
│   ├── main.py             # API endpoints and logic
│   ├── discord_bot.py      # Discord bot integration
│   └── ...                 # Other backend modules
├── frontend/               # Frontend widget and UI
│   └── widget-loader.js    # Embeddable chat widget loader
├── nginx.conf              # Nginx reverse proxy configuration
├── docker-compose.yml      # Docker Compose orchestration file
├── docs/                   # Documentation and diagrams
│   └── bgno_architecture.png
├── medium_article.md       # Medium article draft for publicizing
├── whitepaper.tex          # LaTeX source of the research manuscript
└── README.md               # This file
```

---

## 🤝 Contributing

Contributions are welcome! Please open issues or pull requests for:

- New connectors (e.g., ORCID, PubMed)
- UI/UX improvements
- Bug fixes and optimizations
- Documentation enhancements

---

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 📞 Contact

For questions or collaboration inquiries, please open an issue or contact the maintainers at [your-email@example.com].

---

## 🌐 Links

- [Project Website](https://researchtwin.net)  
- [GitHub Repository](https://github.com/your-org/researchtwin)  
- [ArXiv Paper](https://arxiv.org/abs/XXXX.XXXXX)  
- [Medium Article](https://medium.com/@yourhandle/researchtwin)

---

*Empowering researchers and AI agents to discover, collaborate, and innovate together.*
