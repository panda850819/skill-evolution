#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Evolution - 機會分析腳本

用途：分析 skill 使用數據，識別改進機會，生成演進提案
觸發：手動執行或排程

使用方式：
    python3 analyze-opportunities.py                    # 分析所有 skills
    python3 analyze-opportunities.py --skill pine-lead  # 分析特定 skill
    python3 analyze-opportunities.py --days 7           # 分析最近 7 天
    python3 analyze-opportunities.py --report           # 生成週報
"""

import json
import yaml
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import hashlib

# === 配置 ===
HOME = Path.home()
EVOLUTION_DIR = HOME / ".claude" / "evolution"
SKILLS_DIR = HOME / ".claude" / "skills"
LOGS_DIR = EVOLUTION_DIR / "logs"
PENDING_DIR = EVOLUTION_DIR / "pending"
REPORTS_DIR = EVOLUTION_DIR / "reports"
BACKUPS_DIR = EVOLUTION_DIR / "backups"
CONFIG_DIR = HOME / ".claude" / "skills" / "skill-evolution" / "config"

# 時區設定（UTC+8）
TZ_OFFSET = "+08:00"


# === 數據模型 ===

@dataclass
class SkillMetrics:
    """Skill 使用統計"""
    skill_name: str
    invocation_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    skip_count: int = 0
    avg_duration_ms: float = 0.0
    last_invoked: Optional[str] = None
    error_patterns: List[str] = field(default_factory=list)
    trigger_attempts: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.invocation_count == 0:
            return 0.0
        return self.success_count / self.invocation_count * 100


@dataclass
class EvolutionProposal:
    """演進提案"""
    proposal_id: str
    skill_id: str
    created_at: str
    expires_at: str
    change_level: str  # patch, minor, major
    status: str  # pending, approved, rejected, applied

    source_type: str
    source_session_id: Optional[str]
    source_trigger: str

    title: str
    description: str
    changes: List[Dict[str, Any]]
    impact: List[str]

    backup_path: Optional[str] = None


# === 工具函數 ===

def get_timestamp() -> str:
    """取得 UTC+8 時間戳"""
    return datetime.now().strftime(f"%Y-%m-%dT%H:%M:%S{TZ_OFFSET}")


def load_config() -> Dict[str, Any]:
    """載入配置檔"""
    settings_file = CONFIG_DIR / "settings.yaml"
    if settings_file.exists():
        with open(settings_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def load_rules() -> Dict[str, Any]:
    """載入演進規則"""
    rules_file = CONFIG_DIR / "rules.yaml"
    if rules_file.exists():
        with open(rules_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


def load_logs(days: int = 7) -> List[Dict[str, Any]]:
    """載入最近 N 天的日誌"""
    logs = []
    today = datetime.now()

    for i in range(days):
        date = today - timedelta(days=i)
        log_file = LOGS_DIR / f"{date.strftime('%Y-%m-%d')}.jsonl"

        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            logs.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

    return logs


def get_skill_list() -> List[str]:
    """取得所有 skill 名稱"""
    skills = []
    for skill_dir in SKILLS_DIR.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            name = skill_dir.name
            if name not in ["_archived", "_shared"]:
                skills.append(name)
    return sorted(skills)


def read_skill_file(skill_name: str) -> Optional[str]:
    """讀取 skill 檔案內容"""
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"
    if skill_file.exists():
        with open(skill_file, 'r', encoding='utf-8') as f:
            return f.read()
    return None


def parse_skill_frontmatter(content: str) -> Dict[str, Any]:
    """解析 skill frontmatter"""
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if match:
        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return {}
    return {}


def generate_proposal_id(skill_name: str) -> str:
    """生成提案 ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    hash_suffix = hashlib.md5(f"{skill_name}{timestamp}".encode()).hexdigest()[:6]
    return f"{skill_name}-{hash_suffix}"


# === 分析函數 ===

def analyze_usage_patterns(logs: List[Dict], skills: List[str]) -> Dict[str, SkillMetrics]:
    """分析使用模式"""
    metrics = {skill: SkillMetrics(skill_name=skill) for skill in skills}

    for log in logs:
        # 跳過非 dict 類型的日誌項
        if not isinstance(log, dict):
            continue

        skill = log.get('skill')
        if skill and skill in metrics:
            m = metrics[skill]
            action = log.get('action')

            if action == 'invoked':
                m.invocation_count += 1
                m.last_invoked = log.get('timestamp')

                result = log.get('result', 'success')
                if result == 'success':
                    m.success_count += 1
                else:
                    m.failure_count += 1
                    # 記錄錯誤模式
                    error = log.get('error')
                    if error and error not in m.error_patterns:
                        m.error_patterns.append(error)

                # 記錄持續時間
                duration = log.get('duration_ms', 0)
                if duration > 0:
                    total = m.avg_duration_ms * (m.invocation_count - 1) + duration
                    m.avg_duration_ms = total / m.invocation_count

            elif action == 'skipped':
                m.skip_count += 1
                reason = log.get('reason')
                if reason:
                    m.trigger_attempts.append(reason)

    return metrics


def identify_trigger_opportunities(metrics: Dict[str, SkillMetrics]) -> List[Dict]:
    """識別觸發詞改進機會"""
    opportunities = []

    for skill_name, m in metrics.items():
        # 如果有很多跳過記錄，可能需要改進觸發詞
        if m.skip_count > 3:
            opportunities.append({
                'skill': skill_name,
                'type': 'trigger_improvement',
                'level': 'patch',
                'reason': f"Skill 被跳過 {m.skip_count} 次",
                'attempts': m.trigger_attempts[:5]
            })

    return opportunities


def identify_error_patterns(metrics: Dict[str, SkillMetrics]) -> List[Dict]:
    """識別錯誤模式"""
    opportunities = []

    for skill_name, m in metrics.items():
        # 成功率低於 70%
        if m.invocation_count >= 5 and m.success_rate < 70:
            opportunities.append({
                'skill': skill_name,
                'type': 'error_fix',
                'level': 'minor',
                'reason': f"成功率僅 {m.success_rate:.1f}%",
                'patterns': m.error_patterns[:3]
            })

    return opportunities


def identify_unused_skills(metrics: Dict[str, SkillMetrics], days: int) -> List[Dict]:
    """識別未使用的 skills"""
    opportunities = []

    for skill_name, m in metrics.items():
        # 在分析期間內完全未使用
        if m.invocation_count == 0:
            opportunities.append({
                'skill': skill_name,
                'type': 'unused',
                'level': 'major',
                'reason': f"過去 {days} 天未被使用",
                'suggestion': '考慮改進觸發詞或合併/廢棄'
            })

    return opportunities


def analyze_skill_content(skill_name: str) -> List[Dict]:
    """分析 skill 內容品質"""
    opportunities = []
    content = read_skill_file(skill_name)

    if not content:
        return opportunities

    frontmatter = parse_skill_frontmatter(content)

    # 檢查必要欄位
    if 'description' not in frontmatter:
        opportunities.append({
            'skill': skill_name,
            'type': 'missing_description',
            'level': 'patch',
            'reason': '缺少 description 欄位'
        })

    # 檢查 evolution metadata
    if 'evolution' not in frontmatter:
        opportunities.append({
            'skill': skill_name,
            'type': 'missing_evolution_metadata',
            'level': 'patch',
            'reason': '缺少 evolution metadata'
        })

    # 檢查必要 sections
    required_sections = ['Out of Scope', 'Verification', 'Integrations']
    for section in required_sections:
        if f"## {section}" not in content:
            opportunities.append({
                'skill': skill_name,
                'type': 'missing_section',
                'level': 'minor',
                'reason': f'缺少 {section} section'
            })

    return opportunities


# === 提案生成 ===

def create_proposal(opportunity: Dict) -> EvolutionProposal:
    """根據機會創建提案"""
    skill_name = opportunity['skill']
    proposal_id = generate_proposal_id(skill_name)
    now = get_timestamp()
    expires = (datetime.now() + timedelta(days=7)).strftime(f"%Y-%m-%dT%H:%M:%S{TZ_OFFSET}")

    # 根據類型生成提案內容
    opp_type = opportunity['type']

    if opp_type == 'trigger_improvement':
        title = f"改進 {skill_name} 觸發詞"
        description = f"分析發現 {opportunity['reason']}。\n建議審查並新增觸發詞。"
        changes = [{
            'file': 'SKILL.md',
            'type': 'review',
            'section': 'frontmatter.description',
            'note': '審查觸發詞覆蓋率'
        }]

    elif opp_type == 'error_fix':
        title = f"修復 {skill_name} 錯誤模式"
        description = f"分析發現 {opportunity['reason']}。\n常見錯誤：{', '.join(opportunity.get('patterns', []))}"
        changes = [{
            'file': 'SKILL.md',
            'type': 'review',
            'section': 'workflow',
            'note': '審查工作流程和錯誤處理'
        }]

    elif opp_type == 'unused':
        title = f"審查未使用的 {skill_name}"
        description = f"{opportunity['reason']}\n{opportunity.get('suggestion', '')}"
        changes = [{
            'file': 'SKILL.md',
            'type': 'review',
            'note': '考慮改進、合併或廢棄'
        }]

    elif opp_type == 'missing_evolution_metadata':
        title = f"為 {skill_name} 新增 evolution metadata"
        description = "此 skill 缺少 evolution metadata，無法參與自動演進。"
        changes = [{
            'file': 'SKILL.md',
            'type': 'edit',
            'section': 'frontmatter',
            'add': 'evolution: { enabled: true, version: "1.0.0", auto_evolve: patch }'
        }]

    elif opp_type == 'missing_section':
        section = opportunity['reason'].replace('缺少 ', '').replace(' section', '')
        title = f"為 {skill_name} 新增 {section} section"
        description = f"此 skill 缺少建議的 {section} section。"
        changes = [{
            'file': 'SKILL.md',
            'type': 'edit',
            'section': section,
            'note': f'新增 ## {section}'
        }]

    else:
        title = f"{skill_name} 改進提案"
        description = opportunity.get('reason', '需要審查')
        changes = []

    impact = [opportunity.get('reason', '改進 skill 品質')]

    return EvolutionProposal(
        proposal_id=proposal_id,
        skill_id=skill_name,
        created_at=now,
        expires_at=expires,
        change_level=opportunity.get('level', 'minor'),
        status='pending',
        source_type='session-analysis',
        source_session_id=None,
        source_trigger=opp_type,
        title=title,
        description=description,
        changes=changes,
        impact=impact
    )


def save_proposal(proposal: EvolutionProposal) -> Path:
    """儲存提案到檔案"""
    PENDING_DIR.mkdir(parents=True, exist_ok=True)

    proposal_file = PENDING_DIR / f"{proposal.proposal_id}.yaml"

    # 轉換為 dict
    data = asdict(proposal)

    with open(proposal_file, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return proposal_file


# === 報告生成 ===

def generate_report(
    metrics: Dict[str, SkillMetrics],
    opportunities: List[Dict],
    proposals: List[EvolutionProposal],
    days: int
) -> str:
    """生成分析報告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    week = datetime.now().strftime("%Y-W%W")

    report = f"""# Skill Evolution 分析報告

**生成時間**: {now} (UTC+8)
**分析期間**: 過去 {days} 天
**報告週期**: {week}

---

## 使用統計

| Skill | 調用次數 | 成功率 | 跳過次數 | 最後使用 |
|-------|----------|--------|----------|----------|
"""

    # 按調用次數排序
    sorted_metrics = sorted(metrics.values(), key=lambda m: m.invocation_count, reverse=True)

    for m in sorted_metrics[:20]:  # 只顯示前 20 個
        last = m.last_invoked[:10] if m.last_invoked else "N/A"
        report += f"| {m.skill_name} | {m.invocation_count} | {m.success_rate:.0f}% | {m.skip_count} | {last} |\n"

    report += f"""
---

## 發現的機會

共發現 **{len(opportunities)}** 個改進機會。

### 按類型分類

"""

    # 按類型分組
    by_type = defaultdict(list)
    for opp in opportunities:
        by_type[opp['type']].append(opp)

    type_names = {
        'trigger_improvement': '觸發詞改進',
        'error_fix': '錯誤修復',
        'unused': '未使用 Skills',
        'missing_evolution_metadata': '缺少 Evolution Metadata',
        'missing_section': '缺少必要 Section',
        'missing_description': '缺少 Description'
    }

    for opp_type, opps in by_type.items():
        type_name = type_names.get(opp_type, opp_type)
        report += f"#### {type_name} ({len(opps)} 個)\n\n"
        for opp in opps[:5]:
            report += f"- **{opp['skill']}**: {opp['reason']}\n"
        if len(opps) > 5:
            report += f"- ... 還有 {len(opps) - 5} 個\n"
        report += "\n"

    report += f"""---

## 生成的提案

共生成 **{len(proposals)}** 個演進提案。

| ID | Skill | 級別 | 標題 |
|----|-------|------|------|
"""

    for p in proposals:
        level_emoji = {'patch': '🟢', 'minor': '🟡', 'major': '🔴'}.get(p.change_level, '⚪')
        report += f"| {p.proposal_id} | {p.skill_id} | {level_emoji} {p.change_level} | {p.title} |\n"

    report += f"""
---

## 建議行動

1. **審查 Major 級別提案** - 需要手動確認
2. **等待 Minor 級別提案** - 24 小時後自動執行（可取消）
3. **Patch 級別** - 已自動執行

---

## 下一步

提案檔案位置: `~/.claude/evolution/pending/`

執行命令:
```bash
# 應用 patch 級別更新
python3 ~/.claude/skills/skill-evolution/scripts/apply-update.py --level patch

# 查看所有待處理提案
ls ~/.claude/evolution/pending/
```

---

_報告由 skill-evolution 自動生成_
"""

    return report


def save_report(report: str) -> Path:
    """儲存報告"""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    week = datetime.now().strftime("%Y-W%W")
    report_file = REPORTS_DIR / f"weekly-{week}.md"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    return report_file


# === 主程式 ===

def main():
    parser = argparse.ArgumentParser(
        description='Skill Evolution - 機會分析腳本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python3 analyze-opportunities.py                    # 分析所有 skills
  python3 analyze-opportunities.py --skill pine-lead  # 分析特定 skill
  python3 analyze-opportunities.py --days 14          # 分析最近 14 天
  python3 analyze-opportunities.py --report           # 生成週報
  python3 analyze-opportunities.py --dry-run          # 乾跑模式
        """
    )

    parser.add_argument('--skill', type=str, help='分析特定 skill')
    parser.add_argument('--days', type=int, default=7, help='分析天數 (預設: 7)')
    parser.add_argument('--report', action='store_true', help='生成報告')
    parser.add_argument('--dry-run', action='store_true', help='乾跑模式，不儲存提案')
    parser.add_argument('--verbose', '-v', action='store_true', help='詳細輸出')

    args = parser.parse_args()

    print(f"🔍 Skill Evolution 分析器")
    print(f"📅 分析期間: 過去 {args.days} 天")
    print()

    # 確保目錄存在
    for d in [LOGS_DIR, PENDING_DIR, REPORTS_DIR, BACKUPS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # 載入日誌
    logs = load_logs(args.days)
    print(f"📊 載入 {len(logs)} 條日誌記錄")

    # 取得 skill 列表
    if args.skill:
        skills = [args.skill]
    else:
        skills = get_skill_list()
    print(f"📦 分析 {len(skills)} 個 skills")
    print()

    # 分析使用模式
    print("🔄 分析使用模式...")
    metrics = analyze_usage_patterns(logs, skills)

    # 識別機會
    opportunities = []

    print("🔍 識別觸發詞機會...")
    opportunities.extend(identify_trigger_opportunities(metrics))

    print("🔍 識別錯誤模式...")
    opportunities.extend(identify_error_patterns(metrics))

    print("🔍 識別未使用 skills...")
    opportunities.extend(identify_unused_skills(metrics, args.days))

    print("🔍 分析內容品質...")
    for skill in skills:
        opportunities.extend(analyze_skill_content(skill))

    print(f"\n✅ 發現 {len(opportunities)} 個改進機會")

    # 生成提案
    proposals = []
    for opp in opportunities:
        proposal = create_proposal(opp)
        proposals.append(proposal)

        if not args.dry_run:
            save_proposal(proposal)
            if args.verbose:
                print(f"   📝 {proposal.proposal_id}: {proposal.title}")

    print(f"📝 生成 {len(proposals)} 個提案")

    if args.dry_run:
        print("⚠️  乾跑模式 - 提案未儲存")

    # 生成報告
    if args.report or not args.dry_run:
        print("\n📊 生成報告...")
        report = generate_report(metrics, opportunities, proposals, args.days)

        if not args.dry_run:
            report_file = save_report(report)
            print(f"📄 報告已儲存: {report_file}")
        else:
            print("\n" + "=" * 60)
            print(report)
            print("=" * 60)

    print("\n✅ 分析完成")

    # 輸出摘要
    patch_count = sum(1 for p in proposals if p.change_level == 'patch')
    minor_count = sum(1 for p in proposals if p.change_level == 'minor')
    major_count = sum(1 for p in proposals if p.change_level == 'major')

    print(f"\n📊 提案摘要: 🟢 {patch_count} patch | 🟡 {minor_count} minor | 🔴 {major_count} major")

    if not args.dry_run:
        print(f"\n📁 提案位置: {PENDING_DIR}")


if __name__ == "__main__":
    main()
