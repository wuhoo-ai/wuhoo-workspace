# openclaw-observability

Full-stack observability plugin for [OpenClaw](https://openclaw.ai) — automatically records every LLM call, tool invocation, and agent lifecycle event into a local DuckDB or remote MySQL database, with a built-in web dashboard for tracing, analytics, and security auditing.

## ✨ Features

- **Full-Chain Tracing** — Captures 20 OpenClaw hooks covering LLM calls, tool invocations, agent lifecycle, session management, context compaction, and gateway events
- **Token Usage Tracking** — Automatically injects `stream_options` via fetch interception to capture prompt/completion tokens from any OpenAI-compatible API
- **Dual Storage Backend** — Local mode (embedded DuckDB, zero config) or Remote mode (MySQL/RDS)
- **Built-in Web Dashboard** — Session list, waterfall trace view, analytics charts, and security alerts — all served from the plugin with no external dependencies
- **Security Scanning** — Two-layer detection engine:
  - **L1 Rule Engine** — Regex-based real-time scanning for secrets, dangerous commands, prompt injection, and sensitive file access
  - **L2 Chain Detector** — Cross-action behavioral analysis (e.g., read credentials → exfiltrate data)
- **Automatic Redaction** — Masks API keys, passwords, tokens, and other sensitive fields before storage
- **Async Batch Buffer** — Configurable batch size and flush interval with overflow protection

## 📦 Installation

```bash
openclaw plugins install openclaw-observability
```

That's it. The plugin starts in **Local mode** by default — zero configuration required.

## 🚀 Quick Start

1. Install the plugin (see above)
2. Restart the gateway:
   ```bash
   openclaw gateway restart
   ```
3. Open the dashboard:
   ```
   http://localhost:18789/plugins/observability/
   ```

## 🖥️ Dashboard

The built-in web UI provides four tabs:

### Dashboard (Traces)
- Summary stats: total sessions, actions, tokens, average latency, success rate
- Full-text search across sessions, actions, and content
- Time range filtering (30 min → all time)
- Click any session to open the **waterfall trace view** with nested action timeline and detailed input/output inspector

### Analytics
- Overview KPIs: sessions, tokens (input/output), latency, active models, security alerts
- Activity over time chart (auto-switches between hourly and daily granularity)
- Token usage by model breakdown
- Action type distribution
- Top agents by session/token count

### Security
- Alert statistics by severity (Critical / Warning / Info)
- Filterable alert list with full-text search
- Alert lifecycle management: Acknowledge → Resolve → False Positive
- Direct link from alert to the offending action in the trace view

## ⚙️ Configuration

### Storage Modes

| Mode | Backend | Config Required |
|------|---------|----------------|
| `local` (default) | Embedded DuckDB | None |
| `remote` | MySQL 5.7+ / 8.x / RDS | Connection info |

### Remote Mode (MySQL)

Configure via OpenClaw Dashboard (Settings → Plugins → openclaw-observability Config) or edit `~/.openclaw/openclaw.json`:

```json
{
  "plugins": {
    "entries": {
      "openclaw-observability": {
        "enabled": true,
        "config": {
          "mode": "remote",
          "mysql": {
            "host": "your-mysql-host.com",
            "port": 3306,
            "user": "username",
            "password": "password",
            "database": "openclaw_observability"
          }
        }
      }
    }
  }
}
```

### All Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `mode` | `local` | Storage mode: `local` (DuckDB) or `remote` (MySQL) |
| `duckdb.path` | `~/.openclaw/data/observability.duckdb` | DuckDB database file path (local mode only) |
| `mysql.host` | `localhost` | MySQL host address |
| `mysql.port` | `3306` | MySQL port |
| `mysql.user` | `root` | MySQL username |
| `mysql.password` | `""` | MySQL password |
| `mysql.database` | `openclaw_observability` | MySQL database name (auto-created) |
| `buffer.batchSize` | `50` | Records to accumulate before batch write |
| `buffer.flushIntervalMs` | `5000` | Auto-flush interval in ms |
| `redaction.enabled` | `true` | Automatically redact sensitive fields |
| `redaction.patterns` | `[api_key, password, ...]` | Field name patterns to redact (case-insensitive regex) |
| `security.enabled` | `true` | Enable real-time security scanning |
| `security.rules.*` | `true` | Toggle individual rule categories |
| `security.domainWhitelist` | `[]` | Domains excluded from external request alerts |

## 🔒 Security Rules

### L1 — Pattern-Based Detection

| Rule | Detection | Severity |
|------|-----------|----------|
| S001 | Alibaba Cloud AccessKey leak | Critical |
| S002 | AWS AccessKey leak | Critical |
| S003 | Private key (RSA/EC/SSH) leak | Critical |
| S004 | JWT token leak | Warning |
| S005 | Database connection string leak | Warning |
| S006 | Generic API key leak (OpenAI, GitHub PAT, etc.) | Warning |
| S007 | GCP service account key | Critical |
| S008 | Azure connection string leak | Critical |
| H001 | Dangerous shell commands (`rm -rf`, `curl \| sh`, etc.) | Critical |
| H002 | Sensitive file path access (`.ssh/`, `.env`, etc.) | Warning |
| H003 | Abnormally large data output (>100KB) | Warning |
| H004 | Bulk environment variable access | Warning |
| H005 | Privilege escalation (`sudo`, `su -`, `pkexec`) | Critical |
| T003 | External network request (non-whitelisted domain) | Warning |
| T005 | Prompt injection attack patterns | Warning/Critical |

### L2 — Behavioral Chain Detection

| Chain | Pattern | Severity |
|-------|---------|----------|
| CHAIN-001 | Read sensitive file → outbound network request | Critical |
| CHAIN-002 | Tool returns injection → executes sensitive operation | Critical |

## 🗄️ Database Schema

The plugin automatically creates three tables:

- **`audit_actions`** — Every recorded action (LLM call, tool invocation, etc.)
- **`audit_sessions`** — Aggregated session summaries (auto-updated)
- **`audit_alerts`** — Security alert records

Schema is identical between DuckDB and MySQL backends.

## 📁 Project Structure

```
src/
  index.ts                    # plugin assembly (activate/deactivate + wiring)
  hooks/                      # OpenClaw hook registrations by domain
    messages.ts
    tools.ts
    session.ts
    subagent.ts
  runtime/                    # shared runtime infrastructure
    fetch-interceptor.ts
    session-context.ts
  gateway/
    register-observability-gateway.ts
  storage/                    # writers, schemas, batch buffer
  security/                   # rule engine + chain detector
  web/                        # HTTP routes + API queries + UI bundle source
```

`index.ts` only wires modules together; domain logic lives under `hooks/`, `runtime/`, and `gateway/`.

## 🏗️ Architecture

```
OpenClaw Gateway
  │
  ├── Plugin Hooks (20 hooks)
  │     ├── llm_input / llm_output
  │     ├── before_tool_call / after_tool_call
  │     ├── session_start / session_end
  │     └── ... (agent, message, context, gateway)
  │
  ├── Fetch Interceptor
  │     └── Injects stream_options → Parses SSE usage
  │
  ├── Security Scanner
  │     ├── L1: Pattern rules (15 rules)
  │     └── L2: Chain detector (2 chains)
  │
  ├── Async Batch Buffer
  │     └── batchSize / flushIntervalMs / overflow protection
  │
  ├── Storage Writer
  │     ├── DuckDBLocalWriter (local mode)
  │     └── MySQLWriter (remote mode)
  │
  └── Web Dashboard
        ├── GET /plugins/observability/          → SPA UI
        ├── GET /plugins/observability/api/stats
        ├── GET /plugins/observability/api/sessions
        ├── GET /plugins/observability/api/actions
        ├── GET /plugins/observability/api/alerts
        └── GET /plugins/observability/api/analytics
```

## 📄 License

MIT
