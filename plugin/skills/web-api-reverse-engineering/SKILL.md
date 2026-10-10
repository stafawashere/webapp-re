---
name: web-api-reverse-engineering
description: Reverse engineer web pages to discover APIs and produce OpenAPI 3.1 specs using Chrome automation
---

# Web API Reverse Engineering Skill

> Discover, document, and version APIs from any website using Chrome automation.

This skill helps you systematically reverse engineer web pages to produce OpenAPI 3.1 specifications that can be used for client generation and version tracking.

## Overview

Use this skill when you need to:

- **Discover APIs** - Find open data APIs or reverse engineer web UIs
- **Document endpoints** - Produce OpenAPI 3.1 specs
- **Handle security** - Manage cookies, TLS, CDN bypass
- **Track changes** - Version specs for future updates

## Workflow

### 1. Create Research Epic

Start by creating a beads epic to track multi-session research:

```bash
bd create --title="Reverse engineer [WEBSITE_NAME] API" --type=epic --priority=1 --description="Research and document [WEBSITE_NAME] API.

## Source
URL: [BASE_URL]

## Goals
- Discover API endpoints
- Document pagination patterns
- Map data schemas
- Produce OpenAPI 3.1 spec"
```

### 2. Initial Exploration with Chrome

Use Chrome automation to explore the target site:

```
# Get browser context
mcp__claude-in-chrome__tabs_context_mcp

# Create new tab
mcp__claude-in-chrome__tabs_create_mcp

# Navigate to target
mcp__claude-in-chrome__navigate(url="https://target-site.com")

# Take screenshot
mcp__claude-in-chrome__computer(action="screenshot")
```

### 3. Network Analysis

Monitor network requests to discover API endpoints:

```
# Read network requests
mcp__claude-in-chrome__read_network_requests(tabId=TAB_ID, urlPattern="/api/")

# Filter for API calls
mcp__claude-in-chrome__read_network_requests(tabId=TAB_ID, urlPattern="json")
```

### 4. API Discovery Patterns

#### Pattern A: Open Data APIs
Look for:
- `/api/`, `/rest/`, `/graphql/` endpoints
- CORS headers indicating public APIs
- API documentation links in footer/headers
- OpenAPI/Swagger UI endpoints (`/swagger`, `/docs`, `/openapi.json`)

#### Pattern B: Hidden APIs
Check for:
- XHR/Fetch requests in network tab
- WebSocket connections
- GraphQL endpoints (look for `/graphql` or query batching)
- API version prefixes (`/v1/`, `/v2/`)

#### Pattern C: HTML Scraping
When no API exists:
- Analyze HTML structure with `read_page`
- Identify pagination patterns (`?page=N`, `offset=N`, etc.)
- Map data extraction selectors

### 5. Pagination Analysis

Common patterns to identify:

| Pattern | Example | Description |
|---------|---------|-------------|
| Page number | `?page=2` | Simple page index |
| Offset/Limit | `?offset=50&limit=25` | Record offset |
| Cursor | `?cursor=abc123` | Opaque cursor |
| Link header | `Link: <url>; rel="next"` | HTTP header pagination |
| ArcGIS | `resultOffset=0&resultRecordCount=100` | ESRI style |

### 6. Security Handling

#### Session Cookies (JSESSIONID)

```
# Read page to establish session
mcp__claude-in-chrome__read_page(tabId=TAB_ID)

# Check cookies are set before making requests
mcp__claude-in-chrome__javascript_tool(
  tabId=TAB_ID,
  text="document.cookie"
)
```

#### CDN Bypass (Akamai, Cloudflare)

If blocked by CDN:
1. Add delays between requests
2. Simulate realistic user behavior
3. Use proper headers (User-Agent, Accept)
4. Check for challenge pages

```
# Wait between actions
mcp__claude-in-chrome__computer(action="wait", duration=2)

# Check for challenge
mcp__claude-in-chrome__read_page(tabId=TAB_ID, filter="interactive")
```

### 7. Discovery Notes

Document findings during exploration in the OpenAPI spec's `x-discovery-notes` extension:

#### Login Forms & Authentication

```yaml
x-discovery-notes:
  authentication:
    type: form-login  # form-login, oauth, api-key, certificate, none
    login_url: /login
    form_fields:
      - name: username
        type: text
      - name: password
        type: password
      - name: _csrf
        type: hidden
        source: cookie  # Where to get CSRF token
    session_cookie: JSESSIONID
    token_lifetime: 30m  # If known
    refresh_mechanism: cookie-refresh
```

#### Required Headers

```yaml
x-discovery-notes:
  required_headers:
    User-Agent: "Mozilla/5.0 (compatible; specific-agent-string)"
    Accept: "application/json, text/html"
    Accept-Language: "es-ES,es;q=0.9"
    X-Requested-With: "XMLHttpRequest"  # For AJAX detection
    Referer: "https://site.com/previous-page"  # If required
```

#### Anti-Bot Protections

```yaml
x-discovery-notes:
  anti_bot:
    cdn: akamai  # akamai, cloudflare, custom
    challenges:
      - type: javascript
        bypass: wait-for-execution
      - type: captcha
        bypass: none  # Cannot automate
    rate_limit:
      requests_per_minute: 60
      backoff_strategy: exponential
    fingerprinting:
      - canvas
      - webgl
      - timezone
```

#### Session Management

```yaml
x-discovery-notes:
  session:
    initialization: GET /
    cookies_required:
      - JSESSIONID
      - _akamai_token
    cookie_domain: .site.com
    secure_only: true
    same_site: strict
```

#### TLS Requirements

```yaml
x-discovery-notes:
  tls:
    min_version: TLS1.2
    required_ciphers:
      - TLS_AES_256_GCM_SHA384
    client_certificate: false
    pinning: false
```

#### Special Quirks

```yaml
x-discovery-notes:
  quirks:
    - name: vignette-portal
      description: Uses Vignette CMS with non-standard URL parameters
      example: "vgnextoid=abc123&vgnextchannel=def456"
    - name: double-encoding
      description: Some parameters need URL double-encoding
      affected_params: [query, filter]
    - name: timezone-sensitive
      description: API returns different results based on timezone
      workaround: Set Accept-Timezone header
```

### 8. Schema Analysis

Use JavaScript to extract data types:

```javascript
// Analyze response structure
mcp__claude-in-chrome__javascript_tool(
  tabId=TAB_ID,
  text=`
    const data = window.__DATA__ || {};
    Object.keys(data).map(k => ({
      key: k,
      type: typeof data[k],
      sample: JSON.stringify(data[k]).slice(0, 100)
    }))
  `
)
```

### 8. OpenAPI Spec Generation

Write specs to `docs/openapi/`:

```yaml
openapi: 3.1.0
info:
  title: [Service Name] API
  version: 1.0.0
  description: |
    OpenAPI specification for [Service Name].

    ## Discovery Method
    [API/Scraping/Hybrid]

    ## Pagination
    [Pattern description]

    ## Authentication
    [Cookie/None/API Key]

servers:
  - url: https://[base-url]
    description: [Description]

paths:
  /[endpoint]:
    get:
      operationId: [operationId]
      summary: [Summary]
      parameters:
        - name: page
          in: query
          schema:
            type: integer
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/[Schema]'

components:
  schemas:
    [Schema]:
      type: object
      properties:
        # Document discovered fields
```

### 9. Create Implementation Tickets

After spec is complete:

```bash
bd create --title="Integrate [SERVICE_NAME] API" --type=feature --priority=1 --description="Integrate [SERVICE] based on reverse-engineered spec.

## OpenAPI Spec
See: docs/openapi/[service-name].yaml

## Technical Notes
- Pagination: [pattern]
- Auth: [method]
- Rate limits: [if discovered]"
```

## Example Session

```bash
# 1. Create epic
bd create --title="Reverse engineer Madrid Transparency Portal" --type=epic

# 2. Explore with Chrome
# [Chrome automation commands]

# 3. Document findings in spec
# Write to docs/openapi/portal-transparencia-madrid.yaml

# 4. Create implementation ticket
bd create --title="Integrate Portal Transparencia" --type=feature

# 5. Sync beads
bd sync
```

## Output Location

All OpenAPI specs go in:
```
docs/openapi/[service-name].yaml
```

Naming convention:
- Lowercase with hyphens
- Include organization/region if relevant
- Example: `portal-transparencia-madrid.yaml`

## Best Practices

1. **Always create beads epic first** - Enables multi-session research
2. **Take screenshots** - Document UI state for future reference
3. **Monitor network early** - Catch API calls during page load
4. **Test pagination thoroughly** - Many bugs hide in edge cases
5. **Document rate limits** - If you hit them, note for implementation
6. **Version your specs** - Track changes over time
7. **Cross-reference sources** - Link related APIs/portals
