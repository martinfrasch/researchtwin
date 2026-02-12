# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability in ResearchTwin, please report it responsibly:

1. **Email**: martin@researchtwin.net
2. **Subject line**: `[SECURITY] Brief description`
3. **Do not** open a public GitHub issue for security vulnerabilities.

We will acknowledge receipt within 48 hours and aim to provide an initial assessment within 5 business days.

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest `master` | Yes |
| Older commits | No |

ResearchTwin is pre-1.0 software. We recommend always running the latest version.

## Security Best Practices for Self-Hosted Nodes

If you run a Tier 1 Local Node via `run_node.py`, follow these guidelines:

### Secrets Management

- **Never commit `.env` files** to version control. The `.gitignore` already excludes them.
- Store API keys (`ANTHROPIC_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `GITHUB_TOKEN`) in environment variables or a `.env` file with restricted permissions (`chmod 600 .env`).
- Rotate API keys periodically, especially if you suspect exposure.

### Network Security

- By default, `run_node.py` binds to `localhost:8000`. Do **not** expose this directly to the internet.
- If you need external access, place the application behind a reverse proxy (Nginx, Caddy) with:
  - TLS termination (HTTPS)
  - Rate limiting
  - Security headers (CSP, X-Frame-Options, X-Content-Type-Options)
- The `nginx/researchtwin-ssl.conf` file provides a reference configuration.

### Database Security

- The SQLite database (`data/researchtwin.db`) contains researcher registration data (names, emails, external API identifiers).
- Restrict file permissions: `chmod 600 data/researchtwin.db`
- Back up the database regularly.
- The database file is excluded from version control via `.gitignore`.

### Registration Endpoint

- The `POST /api/register` endpoint includes anti-spam measures (honeypot field, email dedup, input validation).
- In production, apply Nginx rate limiting (see `nginx/researchtwin-ssl.conf` for the `register_limit` zone: 1 request/minute/IP).
- Monitor registration logs for abuse.

### Dependencies

- Keep Python dependencies up to date: `pip install --upgrade -r backend/requirements.txt`
- Review dependency advisories regularly.
- Pin dependency versions in production deployments.

### Docker Deployments

- Run containers as a non-root user (the Dockerfile uses `appuser`).
- Do not expose internal ports directly; use the Nginx reverse proxy.
- Keep Docker and base images updated.

## Scope

The following are **in scope** for security reports:

- Authentication/authorization bypasses
- Injection vulnerabilities (SQL, command, XSS)
- Data exposure or leakage
- CORS misconfigurations
- Rate limiting bypasses

The following are **out of scope**:

- Denial of service via excessive API calls to upstream sources (Semantic Scholar, GitHub, etc.)
- Issues in third-party dependencies (report these upstream, but let us know)
- Social engineering attacks
