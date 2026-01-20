# Skill Evolution

**讓你的 Claude Code skills 像生物一樣演化：自動適應、持續改進、逐步完善。**

繁體中文 | [English](README.md)

---

## 什麼是 Skill Evolution？

Skill Evolution 是一個 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 框架，能夠自動改進你的 skills：

1. **自動收集** - 追蹤 skill 被調用的情況和結果
2. **智能分析** - 識別改進機會和使用模式
3. **覆蓋缺口** - 分析記憶找出未被 skill 化的重複問題
4. **漸進更新** - 根據分級自動或半自動應用改進
5. **完整追蹤** - 記錄演進歷史，支援回滾

---

## 架構

```
┌─────────────────────────────────────────────────────────────┐
│                     SKILL EVOLUTION                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   COLLECT    │───▶│   ANALYZE    │───▶│    APPLY     │   │
│  │   收集數據    │    │   分析機會    │    │   應用更新    │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│         │                   │                   │            │
│         ▼                   ▼                   ▼            │
│  • 使用頻率         • 模式識別          • 自動應用         │
│  • 成功/失敗率      • 改進建議          • 通知用戶         │
│  • 用戶反饋         • 優先排序          • 版本更新         │
│  • 錯誤模式         • 分級評估          • 歷史記錄         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 改動分級

| 級別 | 定義 | 處理方式 | 通知時機 |
|------|------|----------|----------|
| 🟢 **Patch** | 修正 typo、補充說明、新增觸發詞 | 自動執行 | 事後通知 |
| 🟡 **Minor** | 新增 workflow、調整流程順序 | 自動執行 | 事前通知，延遲 24 小時 |
| 🔴 **Major** | 刪除功能、改變核心邏輯 | 需確認 | 事前通知，等待確認 |

---

## 安裝

### 前置需求

- 已安裝 [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- Python 3.9+
- (可選) [claude-mem](https://github.com/anthropics/claude-mem) 記憶整合

### 快速開始

1. Clone 此 repo：
   ```bash
   git clone https://github.com/pdzeng/skill-evolution.git ~/.claude/skills/skill-evolution
   ```

2. 建立演進數據目錄：
   ```bash
   mkdir -p ~/.claude/evolution/{logs,pending,reports,backups}
   ```

3. (可選) 在 `~/.claude/settings.json` 新增 SessionEnd hook：
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

## 使用方式

### 手動觸發

在 Claude Code 中說：
- 「分析 skill 演進機會」
- 「review my skills」
- 「執行 skill 演進」

### 腳本執行

```bash
# 收集最近 session 數據
~/.claude/skills/skill-evolution/scripts/collect-session-data.sh

# 分析改進機會
python3 ~/.claude/skills/skill-evolution/scripts/analyze-opportunities.py

# 應用 patch 級別更新
python3 ~/.claude/skills/skill-evolution/scripts/apply-update.py --level patch

# 應用所有待處理更新（需確認）
python3 ~/.claude/skills/skill-evolution/scripts/apply-update.py --all --confirm
```

---

## 目錄結構

```
skill-evolution/
├── README.md              ← 英文文檔
├── README.zh-TW.md        ← 本檔案
├── LICENSE
├── scripts/
│   ├── collect-session-data.sh    ← 數據收集
│   ├── analyze-opportunities.py   ← 模式分析
│   └── apply-update.py            ← 更新應用
├── config/
│   ├── rules.yaml         ← 演進規則
│   └── settings.yaml      ← 全局設定
├── docs/
│   └── schema.md          ← 數據格式說明
└── examples/
    └── proposal.yaml      ← 提案範例
```

---

## Evolution Proposal 格式

```yaml
proposal_id: pine-lead-001
skill_id: pine-lead
created_at: "2025-01-11T12:00:00+08:00"
expires_at: "2025-01-18T12:00:00+08:00"

change_level: minor
status: pending  # pending | approved | rejected | applied

proposal:
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
```

---

## 整合

### claude-mem (記憶)

查詢 skill 相關記憶：

```python
# 搜尋 skill 使用模式
search(query="skill pine-lead", limit=50)

# 搜尋錯誤模式
search(query="skill error failed", limit=30)
```

### Telegram 通知

在 `config/settings.yaml` 設定：

```yaml
notifications:
  telegram:
    enabled: true
    bot_token: "${TELEGRAM_BOT_TOKEN}"
    chat_id: "-5008242976"
```

### 通知格式範例

**Patch 應用後**：
```
🔧 Skill Evolution (Patch)
📅 2025/01/11 14:30 (UTC+8)

已自動更新：
• pine-lead: 新增觸發詞 "trading strategy"
• skill-creator: 修正 typo

📊 本週演進統計：3 patch, 1 minor
```

**Major 需確認**：
```
🔴 Skill Evolution (Major 需確認)
📅 2025/01/11 14:30 (UTC+8)

以下更新需要您的確認：
• browser-automation: 移除舊版 CDP 連接方式

回覆 "確認" 執行，或 "取消" 放棄
```

---

## 貢獻

歡迎貢獻！提交 PR 前請先閱讀貢獻指南。

1. Fork 此 repo
2. 建立功能分支 (`git checkout -b feature/amazing-feature`)
3. Commit 你的修改 (`git commit -m 'Add amazing feature'`)
4. Push 到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

---

## 授權

MIT License - 詳見 [LICENSE](LICENSE)

---

## 致謝

- 為 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) by Anthropic 打造
- 靈感來自演化計算和持續改進原則
