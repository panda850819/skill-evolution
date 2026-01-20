#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試新的認知協議規則檢查

這個腳本展示如何檢查新加入的認知協議相關規則
"""

import re
from pathlib import Path
from typing import Dict, List

HOME = Path.home()
SKILLS_DIR = HOME / ".claude" / "skills"


def check_cognitive_protocol_rules(skill_name: str) -> List[Dict]:
    """檢查認知協議規則"""
    opportunities = []
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"

    if not skill_file.exists():
        return opportunities

    with open(skill_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 檢查知識傾向模式
    cognitive_patterns = ["Core Question", "Decision Framework", "Trace", "思考框架"]
    has_cognitive = any(pattern in content for pattern in cognitive_patterns)

    if not has_cognitive:
        opportunities.append({
            'skill': skill_name,
            'rule_id': 'knowledge_dump_pattern',
            'type': 'cognitive_protocol',
            'level': 'major',
            'reason': 'Skill 偏向知識傾倒而非思維框架',
            'suggestion': '轉換為認知協議 - 加入 Core Question 和 Decision Framework'
        })

    # 2. 檢查元認知結構
    tracing_patterns = ["Layer", "Trace Up", "Trace Down", "追溯"]
    has_tracing = any(pattern in content for pattern in tracing_patterns)

    if not has_tracing:
        opportunities.append({
            'skill': skill_name,
            'rule_id': 'missing_meta_cognition',
            'type': 'cognitive_protocol',
            'level': 'major',
            'reason': '沒有追溯框架（L1 ↔ L3 ↔ L2）',
            'suggestion': '加入元認知結構 - Trace Up/Down 路徑'
        })

    # 3. 檢查約束詞強度
    strong_words = ["CRITICAL", "MUST", "NEVER", "MANDATORY", "REQUIRED"]
    weak_words = ["you can", "you may", "consider", "optionally"]

    strong_count = sum(content.count(word) for word in strong_words)
    weak_count = sum(content.count(word) for word in weak_words)

    if weak_count > strong_count * 2 and weak_count > 3:
        opportunities.append({
            'skill': skill_name,
            'rule_id': 'weak_constraint_words',
            'type': 'cognitive_protocol',
            'level': 'patch',
            'reason': f'核心規則使用弱約束詞（弱:{weak_count} vs 強:{strong_count}）',
            'suggestion': '強化約束詞 - 將核心規則的 can/may 改為 MUST/CRITICAL'
        })

    # 4. 檢查輸出格式強制
    output_format_patterns = ["MANDATORY OUTPUT", "REQUIRED FORMAT", "必須輸出"]
    has_format = any(pattern in content for pattern in output_format_patterns)

    if not has_format:
        opportunities.append({
            'skill': skill_name,
            'rule_id': 'missing_output_format',
            'type': 'cognitive_protocol',
            'level': 'minor',
            'reason': '沒有明確要求輸出結構',
            'suggestion': '加入 MANDATORY OUTPUT FORMAT section'
        })

    # 5. 檢查 Hook 配置（針對高頻 skills）
    skill_dir = SKILLS_DIR / skill_name
    has_hooks = (skill_dir / "hooks" / "hooks.json").exists()

    # 簡化判斷：如果 skill 看起來像高頻使用（有很多內容），建議加 Hook
    if len(content) > 5000 and not has_hooks:
        opportunities.append({
            'skill': skill_name,
            'rule_id': 'missing_hook_configuration',
            'type': 'cognitive_protocol',
            'level': 'minor',
            'reason': '複雜 Skill 未配置 Hook 強化觸發',
            'suggestion': '生成 Hook 配置 - hooks/hooks.json + eval-hook.sh'
        })

    # 6. 檢查觸發詞覆蓋
    # 檢查是否有中英文觸發詞
    has_english_triggers = bool(re.search(r'[a-zA-Z]{3,}', content[:500]))  # 前 500 字符
    has_chinese_triggers = bool(re.search(r'[\u4e00-\u9fff]{2,}', content[:500]))

    if not (has_english_triggers and has_chinese_triggers):
        opportunities.append({
            'skill': skill_name,
            'rule_id': 'insufficient_trigger_coverage',
            'type': 'cognitive_protocol',
            'level': 'patch',
            'reason': '缺少多語言觸發詞覆蓋',
            'suggestion': '擴展觸發詞 - 加入中英文、錯誤模式、問題詞'
        })

    # 7. 檢查決策框架
    decision_patterns = ["Decision Tree", "Quick Reference", "決策表", "參考表"]
    has_decision = any(pattern in content for pattern in decision_patterns)

    if not has_decision:
        opportunities.append({
            'skill': skill_name,
            'rule_id': 'missing_decision_framework',
            'type': 'cognitive_protocol',
            'level': 'minor',
            'reason': '缺少快速參考表或決策樹',
            'suggestion': '加入決策框架 - Decision Tree 或 Quick Reference'
        })

    return opportunities


def main():
    """主函數 - 測試認知協議規則"""
    print("🔍 測試認知協議規則檢查")
    print("=" * 70)

    # 測試幾個代表性的 skills
    test_skills = [
        "notebooklm",
        "agent-browser",
        "gh-commit-and-push",
        "pine-lead",
        "anthropic-learner"
    ]

    total_opportunities = 0

    for skill_name in test_skills:
        skill_path = SKILLS_DIR / skill_name
        if not skill_path.exists():
            print(f"\n❌ Skill 不存在: {skill_name}")
            continue

        print(f"\n📦 分析 Skill: {skill_name}")
        print("-" * 70)

        opportunities = check_cognitive_protocol_rules(skill_name)

        if opportunities:
            print(f"⚠️  發現 {len(opportunities)} 個認知協議相關機會:")
            for opp in opportunities:
                level_emoji = {
                    'patch': '🟢',
                    'minor': '🟡',
                    'major': '🔴'
                }.get(opp['level'], '⚪')

                print(f"\n  {level_emoji} [{opp['rule_id']}] {opp['level']}")
                print(f"     原因: {opp['reason']}")
                print(f"     建議: {opp['suggestion']}")

            total_opportunities += len(opportunities)
        else:
            print("✅ 未發現認知協議問題")

    print("\n" + "=" * 70)
    print(f"📊 總計發現 {total_opportunities} 個認知協議相關改進機會")
    print("\n💡 這些是新規則檢測到的機會，展示了如何將 Skills 從知識庫轉換為認知協議")


if __name__ == "__main__":
    main()
