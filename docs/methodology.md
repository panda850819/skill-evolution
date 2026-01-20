# Skill Design Methodology

> 從 rust-skills 文章提取的核心方法論，區分單一 Skill 和 Skills System 兩個層次

## 核心理念

### Skills 是認知協議，不是知識庫

> "A Skill is a Cognitive Protocol that shapes **HOW** Claude thinks about a problem, not **WHAT** it knows."

```
❌ 知識庫思維：提供資訊讓 Claude 參考
✅ 認知協議思維：改變 Claude 處理問題的方式
```

**區別**：
- 知識庫：「Arc 是原子引用計數指標...」
- 認知協議：「當你看到這個錯誤，問自己：為什麼設計需要在兩處使用同一個值？」

---

## 兩層設計架構

```
┌─────────────────────────────────────────────────────────────┐
│                    Skills System                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Router Skill (入口/路由)                            │    │
│  └───────────────────┬─────────────────────────────────┘    │
│                      │                                       │
│    ┌─────────────────┼─────────────────┐                    │
│    ▼                 ▼                 ▼                    │
│  ┌─────┐          ┌─────┐          ┌─────┐                 │
│  │Skill│          │Skill│          │Skill│   ← 單一 Skill  │
│  │  A  │          │  B  │          │  C  │                  │
│  └─────┘          └─────┘          └─────┘                  │
└─────────────────────────────────────────────────────────────┘
```

| 層次 | 複雜度 | 適用場景 |
|------|--------|---------|
| **單一 Skill** | 低-中 | 單一任務、單一領域 |
| **Skills System** | 高 | 跨領域、複雜工作流 |

---

# Part 1: 單一 Skill 設計

大部分 Skills 屬於這個層次。專注於做好一件事。

## 複雜度分級

| 級別 | 類型 | 例子 | 需要的設計元素 |
|------|------|------|---------------|
| L1 | 簡單工具 | gh-commit-and-push, prefer-pnpm | 清晰指令 + 步驟 |
| L2 | 流程引導 | notebooklm, openspec | Decision Flow + Checklist |
| L3 | 認知協議 | debugging, brainstorming | Core Question + 強約束詞 |

## 核心設計元素（4 個）

### 1. Core Question

引導思考而非直接給答案。

**❌ 知識傾倒**：
```markdown
## 什麼是 E0382？
E0382 是 "use of moved value" 錯誤。當一個值被移動後...
```

**✅ 認知協議**：
```markdown
## Core Question

**為什麼我的設計需要在兩處使用同一個值？**

不是問「怎麼修」，而是問「為什麼會這樣」。
```

### 2. 強約束詞

約束詞強度直接影響 Claude 遵循指令的概率。

| 等級 | 約束詞 | 遵循率 | 使用場景 |
|------|--------|--------|---------|
| L5 | CRITICAL, MUST, NEVER, MANDATORY | ~100% | 核心規則 |
| L4 | IMPORTANT, REQUIRED, ALWAYS | ~90% | 重要步驟 |
| L3 | should, recommended | ~70% | 建議 |
| L2 | can, may | ~50% | 選項 |
| L1 | optionally | ~30% | 邊緣情況 |

**應用**：
```markdown
❌ You can consider using Arc if needed.
✅ CRITICAL: You MUST use Arc<T> when sharing data across threads.
```

### 3. Quick Reference

快速決策參考表，減少 Claude 的思考負擔。

```markdown
## Quick Reference

| 情境 | 選擇 | 原因 |
|------|------|------|
| 單線程共享 | Rc<T> | 無需原子操作開銷 |
| 多線程共享 | Arc<T> | 需要 Send + Sync |
| 需要修改 | Arc<Mutex<T>> | 內部可變性 |
```

### 4. MANDATORY OUTPUT（需要時）

當需要固定輸出格式時使用。

```markdown
## MANDATORY OUTPUT FORMAT

Your response MUST include:

### Analysis
[問題分析]

### Solution
[解決方案]

### Verification
[驗證步驟]

CRITICAL: Do not skip any section.
```

## 單一 Skill 模板

```markdown
---
name: skill-name
description: |
  CRITICAL: Use for [purpose]. Triggers on:
  keyword1, keyword2, 中文觸發詞
---

# Skill Name

> 一句話描述這個 Skill 解決什麼問題

## Core Question

**[引導性問題，不是直接答案]?**

## Quick Reference

| 情境 | 選擇 | 原因 |
|------|------|------|
| ... | ... | ... |

## Workflow

CRITICAL: Follow these steps in order.

1. **Step 1**: [描述]
2. **Step 2**: [描述]
3. **Step 3**: [描述]

## Out of Scope

- [這個 Skill 不處理的事項]

## Verification

```bash
# 驗證命令
```

完成標準：
- [ ] [檢查項 1]
- [ ] [檢查項 2]
```

## 單一 Skill 檢查清單

- [ ] 有 Core Question 或 Decision Framework？
- [ ] 核心指令使用強約束詞（MUST/CRITICAL）？
- [ ] 有 Quick Reference 表格？
- [ ] 有 Out of Scope 邊界定義？
- [ ] 有 Verification 驗證方式？
- [ ] 觸發詞包含中英文？

---

# Part 2: Skills System 設計

當多個相關 Skills 需要協作解決複雜問題時，考慮設計 Skills System。

## 何時需要 Skills System？

| 信號 | 說明 |
|------|------|
| 跨多個子領域 | 一個問題涉及不同專業知識 |
| 複雜工作流 | 需要多階段、多步驟協作 |
| 共享規則 | 多個 Skills 有共同的配置或規則 |
| 觸發率低 | 單一 Skill 難以準確觸發 |

## Skills System 架構

```
skills-system/
├── router-skill/        ← 入口路由
│   └── SKILL.md
├── layer-1/             ← 機制/語法層
│   ├── skill-a/
│   └── skill-b/
├── layer-2/             ← 設計/架構層
│   ├── skill-c/
│   └── skill-d/
├── layer-3/             ← 領域/業務層
│   ├── domain-x/
│   └── domain-y/
├── shared/              ← 共享資源
│   └── references/
│       └── common-rules.md
└── hooks/               ← 強制觸發（可選）
    └── hooks.json
```

## System 設計元素

### 1. Router Skill（入口路由）

負責語義識別和智能路由。

```markdown
---
name: system-router
description: |
  CRITICAL: Entry point for [system]. Triggers on:
  [廣泛的關鍵詞覆蓋]
---

# System Router

## Routing Logic

CRITICAL: Analyze the user's question and load appropriate Skills.

| 關鍵詞檢測 | 加載的 Skill |
|-----------|-------------|
| 語法錯誤, E0xxx | layer-1/mechanism-skill |
| 設計, 架構, 模式 | layer-2/design-skill |
| Web, API, HTTP | layer-3/domain-web |

## Dual-Skill Loading

**IMPORTANT**: When domain keywords are detected, load BOTH:
1. Mechanism Skill (L1) - 解決表面問題
2. Domain Skill (L3) - 提供領域約束

Example:
- "Web API 報錯 Send not satisfied"
- Load: mechanism-concurrency + domain-web
```

### 2. 三層追溯模型

```
L1 (表面問題) ← 語法錯誤、API 失敗
     ↑ Trace UP
L3 (領域約束) ← 業務規則、合規要求
     ↓ Trace DOWN
L2 (設計決策) ← 架構模式、技術選型
```

**不是所有 System 都需要這三層**，但這是一個有用的思考框架。

### 3. 共享規則（DRY）

```
shared/references/common-rules.md
```

在各 Skill 中引用：
```markdown
**IMPORTANT**: Before proceeding, read `../shared/references/common-rules.md`
```

**注意**：
- 熱加載**不支持** Skill 本身的 symlink
- 但 references/ 內的 symlink **可以用**

### 4. Hook 機制（可選）

提升觸發率從 ~50% 到 ~90%。

**何時需要**：
- System 觸發詞複雜
- 需要強制認知框架
- 觸發率長期偏低

**hooks/hooks.json**：
```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "matcher": "(?i)(keyword1|keyword2|E0\\d{3}|中文詞)",
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/.claude/hooks/eval.sh"
      }]
    }]
  }
}
```

**.claude/hooks/eval.sh**：
```bash
#!/bin/bash
cat << 'EOF'
=== MANDATORY: [System Name] FRAMEWORK ===

CRITICAL: You MUST use the [system-router] skill.

1. Identify the problem layer (L1/L2/L3)
2. Load appropriate Skills
3. Follow the complete reasoning process

Do NOT skip the skill or provide quick fixes.
EOF
```

## Skills System 範例

### rust-skills（文章的例子）
```
rust-skills/
├── rust-router          ← 入口
├── m01-m07              ← L1 語言機制
├── m09-m15              ← L2 設計模式
├── domain-*             ← L3 領域約束
├── rust-learner         ← 信息獲取
└── hooks/               ← 強制觸發
```

### superpowers（現有的）
```
superpowers/
├── using-superpowers    ← 入口指南
├── brainstorming        ← 創意階段
├── writing-plans        ← 規劃階段
├── executing-plans      ← 執行階段
├── debugging            ← 問題解決
├── code-reviewer        ← 審查階段
└── ...
```

### 潛在的 System
```
trading-system/
├── trading-router       ← 入口
├── pine-lead            ← Pine Script
├── quant-analyst        ← 量化分析
└── domain-crypto/       ← 加密貨幣領域
```

## Skills System 檢查清單

- [ ] 有明確的 Router/入口 Skill？
- [ ] Skills 按層級或階段組織？
- [ ] 有共享的 references？
- [ ] Router 實現雙技能加載邏輯？
- [ ] 觸發率是否需要 Hook 強化？

---

# Part 3: 演進建議

## 評估流程

```
分析 Skill
    ↓
判斷類型：單一 Skill or Skills System?
    ↓
┌─────────────────┬─────────────────┐
│   單一 Skill     │  Skills System  │
├─────────────────┼─────────────────┤
│ Core Question?  │ Router 完整?    │
│ 強約束詞?       │ 分層覆蓋?       │
│ Quick Ref?      │ 共享規則?       │
│ Out of Scope?   │ Hook 需要?      │
└─────────────────┴─────────────────┘
    ↓
生成改進建議
```

## 常見改進模式

### 單一 Skill 改進

| 問題 | 解決方案 | 級別 |
|------|---------|------|
| 缺少引導性問題 | 加入 Core Question section | minor |
| 約束詞太弱 | 強化為 MUST/CRITICAL | patch |
| 缺少決策參考 | 加入 Quick Reference 表 | minor |
| 輸出格式不明 | 加入 MANDATORY OUTPUT | minor |

### Skills System 改進

| 問題 | 解決方案 | 級別 |
|------|---------|------|
| 缺少入口路由 | 創建 Router Skill | major |
| Skills 孤立 | 抽取共享規則 | minor |
| 觸發率低 | 添加 Hook 配置 | minor |
| 缺少領域覆蓋 | 添加 Domain Skill | major |

---

## References

- **rust-skills**: https://github.com/ZhangHanDong/rust-skills
- **原文**: 「平衡的艺术：rust-skills 及其高级 Skills 技艺探索」
- **核心洞察**: Skills 是認知協議，不是知識庫
- **架構分層**: 單一 Skill（簡單）vs Skills System（複雜）
