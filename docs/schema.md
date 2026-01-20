# Skill Evolution - 數據格式說明

此文件定義 skill-evolution 框架使用的所有數據格式。

---

## 目錄

1. [日誌格式](#日誌格式)
2. [提案格式](#提案格式)
3. [報告格式](#報告格式)
4. [配置格式](#配置格式)

---

## 日誌格式

日誌儲存在 `~/.claude/evolution/logs/YYYY-MM-DD.jsonl`，採用 JSON Lines 格式。

### Skill 調用記錄

```json
{
  "timestamp": "2025-01-11T12:00:00+08:00",
  "session_id": "abc123",
  "skill": "pine-lead",
  "action": "invoked",
  "result": "success",
  "duration_ms": 1500,
  "error": null
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| timestamp | string | ISO 8601 時間戳（UTC+8） |
| session_id | string | Claude session ID |
| skill | string | Skill 名稱 |
| action | enum | invoked, skipped, failed |
| result | enum | success, failure, cancelled |
| duration_ms | number | 執行時間（毫秒） |
| error | string | 錯誤訊息（如有） |

### Skill 跳過記錄

```json
{
  "timestamp": "2025-01-11T12:30:00+08:00",
  "skill": "quant-analyst",
  "action": "skipped",
  "reason": "user-cancelled"
}
```

### Skills 快照

每天第一次收集時記錄：

```json
{
  "timestamp": "2025-01-11T00:00:00+08:00",
  "action": "snapshot",
  "skill_count": 29,
  "skills": ["skill-1", "skill-2", "..."]
}
```

### 演進應用記錄

```json
{
  "timestamp": "2025-01-11T14:00:00+08:00",
  "action": "evolution_applied",
  "skill": "pine-lead",
  "version_before": "1.0.0",
  "version_after": "1.0.1",
  "change_level": "patch",
  "description": "新增觸發詞"
}
```

---

## 提案格式

提案儲存在 `~/.claude/evolution/pending/{proposal_id}.yaml`。

### 完整提案範例

```yaml
proposal_id: pine-lead-abc123
skill_id: pine-lead
created_at: "2025-01-11T12:00:00+08:00"
expires_at: "2025-01-18T12:00:00+08:00"
change_level: patch
status: pending

source_type: session-analysis
source_session_id: "session-456"
source_trigger: trigger_improvement

title: "新增觸發詞 'trading strategy'"
description: |
  分析發現用戶多次嘗試用 "trading strategy" 觸發 pine-lead，
  但因缺少此觸發詞而失敗。建議新增此觸發詞。

changes:
  - file: SKILL.md
    type: edit
    section: frontmatter.description
    before: 'Triggers on "Pine Script", "TradingView"'
    after: 'Triggers on "Pine Script", "TradingView", "trading strategy"'

impact:
  - 提高 skill 觸發率
  - 不影響現有功能

backup_path: "~/.claude/evolution/backups/pine-lead-v1.0.0.md"

# 以下欄位在應用後填入
applied_at: null
rolled_back_at: null
```

### 欄位說明

| 欄位 | 類型 | 必要 | 說明 |
|------|------|------|------|
| proposal_id | string | 是 | 唯一識別碼 |
| skill_id | string | 是 | 目標 skill 名稱 |
| created_at | datetime | 是 | 建立時間 |
| expires_at | datetime | 是 | 過期時間（7 天） |
| change_level | enum | 是 | patch, minor, major |
| status | enum | 是 | pending, approved, rejected, applied, expired, rolled_back |
| source_type | string | 是 | 觸發來源類型 |
| source_session_id | string | 否 | 相關 session ID |
| source_trigger | string | 是 | 觸發原因 |
| title | string | 是 | 提案標題 |
| description | string | 是 | 詳細說明 |
| changes | array | 是 | 變更清單 |
| impact | array | 是 | 影響說明 |
| backup_path | string | 否 | 備份路徑 |
| applied_at | datetime | 否 | 應用時間 |
| rolled_back_at | datetime | 否 | 回滾時間 |

### Change 物件格式

```yaml
- file: SKILL.md
  type: edit          # edit, add, remove, review
  section: frontmatter.description
  before: "舊內容"    # type=edit 時使用
  after: "新內容"     # type=edit 時使用
  add: "新增內容"     # type=add 時使用
  note: "說明"        # type=review 時使用
```

### Status 狀態流轉

```
pending → approved → applied
    ↓         ↓         ↓
    └→ rejected   rolled_back
    ↓
    └→ expired
```

---

## 報告格式

週報儲存在 `~/.claude/evolution/reports/weekly-YYYY-WXX.md`。

### 報告結構

```markdown
# Skill Evolution 分析報告

**生成時間**: YYYY-MM-DD HH:MM (UTC+8)
**分析期間**: 過去 7 天
**報告週期**: YYYY-WXX

---

## 使用統計

| Skill | 調用次數 | 成功率 | 跳過次數 | 最後使用 |
|-------|----------|--------|----------|----------|
| ...   | ...      | ...    | ...      | ...      |

---

## 發現的機會

### 按類型分類

#### 觸發詞改進 (N 個)
- **skill-name**: 原因

#### 錯誤修復 (N 個)
- **skill-name**: 原因

...

---

## 生成的提案

| ID | Skill | 級別 | 標題 |
|----|-------|------|------|
| ...| ...   | ...  | ...  |

---

## 建議行動

1. ...
2. ...

---
```

---

## 配置格式

### settings.yaml

```yaml
config_version: "1.0.0"

notification:
  enabled: true
  telegram:
    enabled: true
    chat_id: "-5008242976"

auto_evolution:
  enabled: true
  levels:
    patch:
      auto_apply: true
      notify: after
    minor:
      auto_apply: true
      delay_minutes: 1440
    major:
      auto_apply: false
      require_confirm: true

data_collection:
  enabled: true
  retention:
    logs_days: 30
    reports_days: 90

analysis:
  default_days: 7
  thresholds:
    low_success_rate: 70
    high_skip_count: 3
```

### rules.yaml

```yaml
rules_version: "1.0.0"

change_levels:
  patch:
    includes:
      - type: typo_fix
      - type: add_trigger
      - type: clarify_description

  minor:
    includes:
      - type: add_section
      - type: reorder_workflow

  major:
    includes:
      - type: remove_feature
      - type: breaking_change

opportunity_rules:
  usage_patterns:
    - id: low_success_rate
      condition:
        metric: success_rate
        threshold: 70

  content_quality:
    - id: missing_evolution_metadata
      condition:
        check: has_evolution_metadata
```

---

## 版本歷史

| 版本 | 日期 | 說明 |
|------|------|------|
| 1.0.0 | 2025-01-11 | 初始版本 |
