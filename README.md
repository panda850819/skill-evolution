# Skill Evolution

**Make your Claude Code skills evolve like living organisms: auto-adapt, continuously improve, and gradually perfect.**

[繁體中文](README.zh-TW.md) | English

---

## What is Skill Evolution?

Skill Evolution is a framework for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) that enables automatic improvement of your skills through:

1. **Automatic Collection** - Track skill invocations and results
2. **Intelligent Analysis** - Identify improvement opportunities and usage patterns
3. **Coverage Gap Detection** - Find repetitive problems that should be "skill-ified"
4. **Gradual Updates** - Apply improvements based on severity levels
5. **Full History** - Track evolution history with rollback support

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     SKILL EVOLUTION                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   COLLECT    │───▶│   ANALYZE    │───▶│    APPLY     │   │
│  │  Gather Data │    │Find Patterns │    │Apply Updates │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│         │                   │                   │            │
│         ▼                   ▼                   ▼            │
│  • Usage frequency    • Pattern detection • Auto-apply      │
│  • Success/fail rate  • Suggestions      • Notifications    │
│  • User feedback      • Prioritization   • Version bump     │
│  • Error patterns     • Level assessment • History log      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Change Levels

| Level | Definition | Handling | Notification |
|-------|------------|----------|--------------|
| 🟢 **Patch** | Typo fixes, docs additions, new trigger words | Auto-execute | After the fact |
| 🟡 **Minor** | New workflows, flow reordering | Auto-execute | 24h delay notification |
| 🔴 **Major** | Feature removal, core logic changes | Requires confirmation | Wait for approval |

---

## Installation

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- Python 3.9+
- (Optional) [claude-mem](https://github.com/anthropics/claude-mem) for memory integration

### Quick Start

1. Clone this repository:
   ```bash
   git clone https://github.com/pdzeng/skill-evolution.git ~/.claude/skills/skill-evolution
   ```

2. Create evolution data directories:
   ```bash
   mkdir -p ~/.claude/evolution/{logs,pending,reports,backups}
   ```

3. (Optional) Add SessionEnd hook to `~/.claude/settings.json`:
   ```json
   {
     "SessionEnd": [
       {
         "hooks": [
           {
             "type": "command",
             "command": "~/.claude/skills/skill-evolution/scripts/collect-session-data.sh"
           }
         ]
       }
     ]
   }
   ```

---

## Usage

### Manual Trigger

In Claude Code, say:
- "Analyze skill evolution opportunities"
- "Review my skills"
- "Execute skill evolution"

### Script Execution

```bash
# Collect recent session data
~/.claude/skills/skill-evolution/scripts/collect-session-data.sh

# Analyze improvement opportunities
python3 ~/.claude/skills/skill-evolution/scripts/analyze-opportunities.py

# Apply patch-level updates
python3 ~/.claude/skills/skill-evolution/scripts/apply-update.py --level patch

# Apply all pending updates (requires confirmation)
python3 ~/.claude/skills/skill-evolution/scripts/apply-update.py --all --confirm
```

---

## Directory Structure

```
skill-evolution/
├── README.md              ← This file
├── README.zh-TW.md        ← Chinese documentation
├── LICENSE
├── scripts/
│   ├── collect-session-data.sh    ← Data collection
│   ├── analyze-opportunities.py   ← Pattern analysis
│   └── apply-update.py            ← Update application
├── config/
│   ├── rules.yaml         ← Evolution rules
│   └── settings.yaml      ← Global settings
├── docs/
│   └── schema.md          ← Data format spec
└── examples/
    └── proposal.yaml      ← Example proposal
```

---

## Evolution Proposal Format

```yaml
proposal_id: pine-lead-001
skill_id: pine-lead
created_at: "2025-01-11T12:00:00+08:00"
expires_at: "2025-01-18T12:00:00+08:00"

change_level: minor
status: pending  # pending | approved | rejected | applied

proposal:
  title: "Add trigger word 'trading strategy'"
  description: |
    Analysis found users trying to trigger pine-lead with
    "trading strategy" but failing due to missing trigger word.

  changes:
    - file: SKILL.md
      type: edit
      section: frontmatter.description
      before: 'Triggers on "Pine Script", "TradingView"'
      after: 'Triggers on "Pine Script", "TradingView", "trading strategy"'
```

---

## Integrations

### claude-mem (Memory)

Query skill-related memories:

```python
# Search skill usage patterns
search(query="skill pine-lead", limit=50)

# Search error patterns
search(query="skill error failed", limit=30)
```

### Telegram Notifications

Configure in `config/settings.yaml`:

```yaml
notifications:
  telegram:
    enabled: true
    bot_token: "${TELEGRAM_BOT_TOKEN}"
    chat_id: "-5008242976"
```

---

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- Built for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) by Anthropic
- Inspired by evolutionary computing and continuous improvement principles
