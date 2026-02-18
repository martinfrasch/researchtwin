# Email Service Setup

ResearchTwin uses transactional email to send 6-digit verification codes for profile updates. The service is powered by [Brevo](https://www.brevo.com/) (formerly Sendinblue) SMTP relay.

## Architecture

```
User requests update → POST /api/request-update
  → Validates slug + email match
  → Rate limit check (max 3 codes/hour/slug)
  → Generates 6-digit code, stores SHA-256 hash in SQLite
  → Sends code via SMTP (backend/email_service.py)
  → Returns 200 or 503 if email delivery fails

User submits code → PATCH /api/researcher/{slug}
  → Verifies code against stored hash (max 5 attempts per code)
  → Applies profile updates
  → Code expires after 1 hour
```

## Environment Variables

Set in `/opt/researchtwin/.env` on the production server:

| Variable | Value | Description |
|----------|-------|-------------|
| `SMTP_HOST` | `smtp-relay.brevo.com` | Brevo SMTP relay server |
| `SMTP_PORT` | `587` | STARTTLS port |
| `SMTP_USER` | `(Brevo login)` | SMTP login from Brevo dashboard |
| `SMTP_PASS` | `(Brevo SMTP key)` | SMTP key (not API key) from Brevo |
| `SMTP_FROM` | `noreply@researchtwin.net` | Sender address |

These are passed to the Docker container via `docker-compose.yml` environment section.

**If `SMTP_HOST` is empty**, the service falls back to printing codes to the container console and the API returns HTTP 503 to the user.

## DNS Records (SiteGround)

DNS is managed at SiteGround (`ns1.siteground.net` / `ns2.siteground.net`).

| Type | Name | Value | Purpose |
|------|------|-------|---------|
| CNAME | `brevo1._domainkey.researchtwin.net` | `b1.researchtwin-net.dkim.brevo.com` | DKIM signing key 1 |
| CNAME | `brevo2._domainkey.researchtwin.net` | `b2.researchtwin-net.dkim.brevo.com` | DKIM signing key 2 |
| TXT | `researchtwin.net` | `v=spf1 +a +mx include:...dnssmarthost.net include:spf.brevo.com ~all` | SPF authorization |
| TXT | `_dmarc.researchtwin.net` | `v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com` | DMARC policy (monitoring) |
| TXT | `researchtwin.net` | `brevo-code:8f8463fb24c7830b3b58e1e7e2da80a4` | Brevo domain verification |

## Key Files

| File | Role |
|------|------|
| `backend/email_service.py` | SMTP sending logic, env var loading, fallback handling |
| `backend/main.py` (line ~618) | `POST /api/request-update` endpoint |
| `backend/researchers.py` | Token generation, hashing, verification, rate limiting |
| `frontend/update.html` | Profile update UI (3-step: request code → enter code → update fields) |
| `docker-compose.yml` | Passes SMTP_* env vars to backend container |

## Security

- Codes are **6-digit numeric**, stored as **SHA-256 hashes** (plaintext never persisted)
- **Rate limited**: max 3 codes per slug per hour (HTTP 429)
- **Attempt limited**: max 5 verification attempts per code
- **Expiry**: codes expire after 1 hour
- **Email verification**: requester must supply the email on file for the slug (HTTP 403 on mismatch)

## Brevo Dashboard

- **Login**: [app.brevo.com](https://app.brevo.com)
- **SMTP keys**: Settings → SMTP & API → SMTP tab
- **Domain auth**: Settings → Senders, Domains & Dedicated IPs → Domains
- **Free tier**: 300 emails/day (sufficient for current scale)

## Troubleshooting

**"Email service is temporarily unavailable" (HTTP 503)**
- Check `SMTP_HOST` is set: `docker exec researchtwin_backend env | grep SMTP`
- Check container logs: `docker logs researchtwin_backend 2>&1 | grep email_service`
- Verify Brevo SMTP key hasn't been revoked in the Brevo dashboard

**Emails landing in spam**
- Verify DKIM: `dig CNAME brevo1._domainkey.researchtwin.net +short`
- Verify SPF: `dig TXT researchtwin.net +short` (should include `spf.brevo.com`)
- Verify DMARC: `dig TXT _dmarc.researchtwin.net +short`
- Consider upgrading DMARC policy from `p=none` to `p=quarantine` after monitoring

**User says code never arrived**
- Check logs: `docker logs researchtwin_backend 2>&1 | grep "Code for"`
- If logs show `SMTP not configured` → env vars missing, redeploy
- If logs show `Failed to send` → SMTP credentials issue, check Brevo dashboard
- If no log entry → the request itself failed (check slug/email match)

## Deployment Notes

When deploying with rsync, always exclude both `.env` and `backend/data/`:
```bash
rsync -avz --delete --exclude='.env' --exclude='backend/data' \
  /Users/mfrasch/projects/my_research/ root@94.130.225.75:/opt/researchtwin/
```
