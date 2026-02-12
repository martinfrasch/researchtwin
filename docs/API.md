# ResearchTwin API Reference

**Base URL**: `https://researchtwin.net` (Hosted) or `http://localhost:8000` (Local Node)
**Version**: 0.3.0
**Content-Type**: `application/json`

---

## Core Endpoints

### List Researchers

```
GET /api/researchers
```

Returns all active researchers on this instance.

**Response**:
```json
{
  "researchers": [
    { "slug": "martin-frasch", "display_name": "Martin G. Frasch" }
  ]
}
```

---

### Get Researcher Context

```
GET /api/context/{slug}
```

Returns the full research profile including S-Index, source status, dataset scores, and repo scores. This is the primary endpoint used by the frontend dashboard.

**Parameters**:
| Name | In | Type | Required | Description |
|------|----|------|----------|-------------|
| `slug` | path | string | yes | Researcher slug (e.g. `martin-frasch`) |

**Response**:
```json
{
  "researcher_slug": "martin-frasch",
  "display_name": "Martin G. Frasch",
  "s_index": 4.72,
  "paper_impact": 18.3,
  "summary": { "total_datasets": 5, "total_repos": 12, "..." : "..." },
  "sources": {
    "semantic_scholar": { "status": "connected", "paper_count": 45, "citation_count": 1200, "h_index": 18 },
    "google_scholar": { "status": "connected", "i10_index": 22 },
    "github": { "status": "connected", "total_repos": 12, "total_stars": 45 },
    "figshare": { "status": "connected", "total_datasets": 5, "total_downloads": 800 }
  },
  "dataset_scores": [ { "title": "...", "doi": "...", "qic": 7.2, "..." : "..." } ],
  "repo_scores": [ { "name": "...", "qic": 6.1, "..." : "..." } ]
}
```

---

### Chat

```
POST /chat
```

Conversational RAG endpoint. Fetches live data, assembles context, and generates a Claude-powered response about the researcher's work.

**Request Body**:
```json
{
  "message": "What are this researcher's most cited papers?",
  "researcher_slug": "martin-frasch"
}
```

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `message` | string | 1-4096 chars | User's question |
| `researcher_slug` | string | 1-128 chars, slug format | Target researcher |

**Response**:
```json
{
  "reply": "Based on the data, the most cited papers are...",
  "researcher_slug": "martin-frasch"
}
```

**Errors**:
- `404`: Unknown researcher
- `503`: Chat unavailable (no `ANTHROPIC_API_KEY` configured)
- `502`: Pipeline error (upstream API failure)

---

### Health Check

```
GET /health
```

**Response**: `{ "status": "ok" }`

---

## Registration

### Register a New Researcher

```
POST /api/register
```

Creates a new researcher profile. Used by the join page and Tier 1 local nodes registering with the hub.

**Request Body**:
```json
{
  "name": "Jane Doe",
  "email": "jane@university.edu",
  "tier": 3,
  "semantic_scholar_id": "12345678",
  "google_scholar_id": "aBcDeFgHiJk",
  "github_username": "janedoe",
  "figshare_search_name": "Jane Doe",
  "orcid": "0000-0002-1234-5678"
}
```

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `name` | string | yes | 2-100 chars, letters/spaces/hyphens | Display name |
| `email` | string | yes | Valid email, max 254 chars | Contact email |
| `tier` | integer | no | 1-3, default 3 | Federation tier |
| `semantic_scholar_id` | string | no | Numeric, max 20 chars | S2 author ID |
| `google_scholar_id` | string | no | Alphanumeric, max 20 chars | GS profile ID |
| `github_username` | string | no | Valid GH username, max 39 chars | GitHub user |
| `figshare_search_name` | string | no | Max 100 chars | Figshare search name |
| `orcid` | string | no | `XXXX-XXXX-XXXX-XXXX` format | ORCID iD |

**Response** (`201`):
```json
{
  "slug": "jane-doe",
  "display_name": "Jane Doe",
  "tier": 3,
  "message": "Welcome to ResearchTwin! Your profile is live at /?researcher=jane-doe"
}
```

**Errors**:
- `409`: Email already registered
- `422`: Validation error (invalid field format)

**Anti-spam**: A hidden `website` honeypot field silently rejects bot submissions.

---

## Profile Updates

### Request Verification Code

```
POST /api/request-update
```

Sends a 6-digit verification code to the researcher's registered email.

**Request Body**:
```json
{
  "slug": "jane-doe",
  "email": "jane@university.edu"
}
```

**Errors**:
- `404`: Unknown researcher
- `403`: Email does not match this profile
- `429`: Too many requests (max 3 codes per hour per slug)

---

### Update Profile

```
PATCH /api/researcher/{slug}
```

Updates researcher connector IDs after email verification.

**Request Body**:
```json
{
  "slug": "jane-doe",
  "code": "123456",
  "semantic_scholar_id": "87654321",
  "github_username": "janedoe-lab"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `slug` | string | yes | Researcher slug |
| `code` | string | yes | 6-digit verification code |
| `semantic_scholar_id` | string | no | Updated S2 ID |
| `google_scholar_id` | string | no | Updated GS ID |
| `github_username` | string | no | Updated GitHub username |
| `figshare_search_name` | string | no | Updated Figshare name |
| `orcid` | string | no | Updated ORCID |

Only non-empty fields are updated. Omitted or empty fields remain unchanged.

**Response**:
```json
{
  "slug": "jane-doe",
  "message": "Profile updated successfully. 2 field(s) changed."
}
```

**Errors**:
- `400`: Slug mismatch
- `403`: Invalid or expired code
- `404`: Unknown researcher

---

## Inter-Agentic Discovery API

These endpoints are designed for machine-to-machine research discovery. All responses include Schema.org `@type` annotations for semantic interoperability.

### Researcher Profile (Machine-Readable)

```
GET /api/researcher/{slug}/profile
```

Returns a structured profile with HATEOAS links to related resources.

**Response** (`@type: Person`):
```json
{
  "@type": "Person",
  "slug": "martin-frasch",
  "name": "Martin G. Frasch",
  "orcid": "0000-0002-1400-6730",
  "s_index": 4.72,
  "paper_impact": 18.3,
  "summary": { "..." : "..." },
  "resources": {
    "papers": "/api/researcher/martin-frasch/papers",
    "datasets": "/api/researcher/martin-frasch/datasets",
    "repos": "/api/researcher/martin-frasch/repos"
  }
}
```

---

### Papers

```
GET /api/researcher/{slug}/papers
```

**Response** (`@type: ItemList`):
```json
{
  "@type": "ItemList",
  "researcher": "martin-frasch",
  "total": 45,
  "items": [
    {
      "@type": "ScholarlyArticle",
      "title": "Paper Title",
      "year": 2023,
      "citations": 150,
      "url": "https://..."
    }
  ]
}
```

---

### Datasets

```
GET /api/researcher/{slug}/datasets
```

**Response** (`@type: ItemList`):
```json
{
  "@type": "ItemList",
  "researcher": "martin-frasch",
  "total": 5,
  "items": [
    {
      "@type": "Dataset",
      "title": "Dataset Title",
      "doi": "10.6084/m9.figshare.xxxxx",
      "downloads": 200,
      "views": 500,
      "qic_score": 7.2
    }
  ]
}
```

---

### Repositories

```
GET /api/researcher/{slug}/repos
```

**Response** (`@type: ItemList`):
```json
{
  "@type": "ItemList",
  "researcher": "martin-frasch",
  "total": 12,
  "items": [
    {
      "@type": "SoftwareSourceCode",
      "name": "repo-name",
      "description": "Description",
      "stars": 15,
      "forks": 3,
      "language": "Python",
      "qic_score": 6.1
    }
  ]
}
```

---

### Cross-Researcher Discovery

```
GET /api/discover?q={query}&type={type}
```

Searches across all researchers for matching papers, datasets, and repositories.

**Parameters**:
| Name | In | Type | Required | Description |
|------|----|------|----------|-------------|
| `q` | query | string | yes | Search query (2-200 chars) |
| `type` | query | string | no | Filter: `paper`, `dataset`, `repo`, or empty for all |

**Response** (`@type: SearchResultSet`):
```json
{
  "@type": "SearchResultSet",
  "query": "fetal heart rate",
  "type_filter": "paper",
  "total": 12,
  "results": [
    {
      "@type": "ScholarlyArticle",
      "title": "Fetal Heart Rate Analysis...",
      "year": 2022,
      "citations": 45,
      "researcher": "Martin G. Frasch",
      "researcher_slug": "martin-frasch"
    }
  ]
}
```

Results are sorted by QIC score (for datasets/repos) or citation count (for papers). Maximum 50 results returned.

---

### Network Map

```
GET /api/network/map
```

Returns geocoded affiliations for all active researchers. Used for the global network visualization.

**Response** (`@type: NetworkMap`):
```json
{
  "@type": "NetworkMap",
  "total_researchers": 3,
  "researchers": [
    {
      "slug": "martin-frasch",
      "name": "Martin G. Frasch",
      "affiliations": [
        {
          "institution": "University of Washington",
          "city": "Seattle",
          "country": "US",
          "current": true,
          "lat": 47.6553,
          "lng": -122.3035
        }
      ]
    }
  ]
}
```

---

## CORS Policy

| Origin | Allowed |
|--------|---------|
| `https://researchtwin.net` | Yes |
| `http://localhost:8000` | Yes (development) |

Allowed methods: `GET`, `POST`, `PATCH`

## Security Headers

All responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

## Rate Limiting

Rate limiting is enforced at the Nginx layer (production only):

| Endpoint | Limit |
|----------|-------|
| `POST /api/register` | 1 request/minute/IP (burst 3) |
| `POST /api/request-update` | 3 codes/hour/slug (application-level) |
| All other endpoints | No limit (subject to upstream API rate limits) |
