#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill Evolution - 更新應用腳本

用途：應用演進提案，更新 skills，管理版本歷史
觸發：手動執行或自動排程

使用方式：
    python3 apply-update.py                          # 互動模式
    python3 apply-update.py --level patch            # 自動應用 patch 級別
    python3 apply-update.py --all                    # 應用所有（需確認）
    python3 apply-update.py --proposal ID            # 應用特定提案
    python3 apply-update.py --rollback ID            # 回滾特定提案
"""

import os
import json
import yaml
import re
import shutil
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

# === 配置 ===
HOME = Path.home()
EVOLUTION_DIR = HOME / ".claude" / "evolution"
SKILLS_DIR = HOME / ".claude" / "skills"
LOGS_DIR = EVOLUTION_DIR / "logs"
PENDING_DIR = EVOLUTION_DIR / "pending"
REPORTS_DIR = EVOLUTION_DIR / "reports"
BACKUPS_DIR = EVOLUTION_DIR / "backups"
CONFIG_DIR = HOME / ".claude" / "skills" / "skill-evolution" / "config"

# Telegram 設定
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = '-5008242976'

TZ_OFFSET = "+08:00"


# === 枚舉 ===

class ChangeLevel(Enum):
    PATCH = 'patch'
    MINOR = 'minor'
    MAJOR = 'major'


class ProposalStatus(Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    APPLIED = 'applied'
    EXPIRED = 'expired'
    ROLLED_BACK = 'rolled_back'


# === 工具函數 ===

def get_timestamp() -> str:
    """取得 UTC+8 時間戳"""
    return datetime.now().strftime(f"%Y-%m-%dT%H:%M:%S{TZ_OFFSET}")


def get_display_time() -> str:
    """取得顯示用時間"""
    return datetime.now().strftime("%Y/%m/%d %H:%M")


def load_proposal(proposal_id: str) -> Optional[Dict[str, Any]]:
    """載入提案"""
    proposal_file = PENDING_DIR / f"{proposal_id}.yaml"
    if proposal_file.exists():
        with open(proposal_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return None


def save_proposal(proposal: Dict[str, Any]) -> Path:
    """儲存提案"""
    proposal_file = PENDING_DIR / f"{proposal['proposal_id']}.yaml"
    with open(proposal_file, 'w', encoding='utf-8') as f:
        yaml.dump(proposal, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return proposal_file


def list_pending_proposals() -> List[Dict[str, Any]]:
    """列出所有待處理提案"""
    proposals = []
    if PENDING_DIR.exists():
        for f in PENDING_DIR.glob("*.yaml"):
            with open(f, 'r', encoding='utf-8') as file:
                proposal = yaml.safe_load(file)
                if proposal and proposal.get('status') == 'pending':
                    proposals.append(proposal)
    return proposals


def load_settings() -> Dict[str, Any]:
    """載入設定"""
    settings_file = CONFIG_DIR / "settings.yaml"
    if settings_file.exists():
        with open(settings_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}


# === 備份函數 ===

def backup_skill(skill_name: str, version: str) -> Path:
    """備份 skill"""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

    skill_file = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_file.exists():
        raise FileNotFoundError(f"Skill 不存在: {skill_name}")

    backup_file = BACKUPS_DIR / f"{skill_name}-v{version}.md"

    # 如果備份已存在，加上時間戳
    if backup_file.exists():
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_file = BACKUPS_DIR / f"{skill_name}-v{version}-{timestamp}.md"

    shutil.copy2(skill_file, backup_file)
    return backup_file


def restore_skill(skill_name: str, backup_path: Path) -> bool:
    """從備份還原 skill"""
    if not backup_path.exists():
        return False

    skill_file = SKILLS_DIR / skill_name / "SKILL.md"
    shutil.copy2(backup_path, skill_file)
    return True


# === 版本管理 ===

def get_skill_version(skill_name: str) -> str:
    """取得 skill 版本"""
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_file.exists():
        return "0.0.0"

    with open(skill_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 嘗試從 evolution.version 讀取
    match = re.search(r'version:\s*["\']?(\d+\.\d+\.\d+)["\']?', content)
    if match:
        return match.group(1)

    return "1.0.0"


def increment_version(version: str, level: ChangeLevel) -> str:
    """增加版本號"""
    parts = version.split('.')
    if len(parts) != 3:
        parts = ['1', '0', '0']

    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

    if level == ChangeLevel.PATCH:
        patch += 1
    elif level == ChangeLevel.MINOR:
        minor += 1
        patch = 0
    elif level == ChangeLevel.MAJOR:
        major += 1
        minor = 0
        patch = 0

    return f"{major}.{minor}.{patch}"


def update_skill_version(skill_name: str, new_version: str, change_description: str) -> bool:
    """更新 skill 版本"""
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_file.exists():
        return False

    with open(skill_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 更新版本號
    content = re.sub(
        r'(version:\s*["\']?)(\d+\.\d+\.\d+)(["\']?)',
        f'\\g<1>{new_version}\\g<3>',
        content
    )

    # 更新 updated 時間
    today = datetime.now().strftime("%Y-%m-%d")
    content = re.sub(
        r'(updated:\s*)[\d-]+',
        f'\\g<1>{today}',
        content
    )

    # 添加歷史記錄（如果有 Changelog section）
    if '## Changelog' in content:
        changelog_entry = f"\n### v{new_version} ({today})\n\n- {change_description}\n"
        content = content.replace('## Changelog', f'## Changelog\n{changelog_entry}')

    with open(skill_file, 'w', encoding='utf-8') as f:
        f.write(content)

    return True


# === 通知函數 ===

def send_telegram_notification(message: str) -> bool:
    """發送 Telegram 通知"""
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️  未設定 TELEGRAM_BOT_TOKEN，跳過通知")
        return False

    try:
        import subprocess

        # 使用 jq 處理 JSON
        cmd = [
            '/usr/bin/curl', '-s', '-X', 'POST',
            f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps({
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            })
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    except Exception as e:
        print(f"⚠️  發送通知失敗: {e}")
        return False


def notify_patch_applied(proposals: List[Dict]) -> None:
    """通知 Patch 應用完成"""
    time = get_display_time()
    message = f"🔧 Skill Evolution (Patch)\n📅 {time} (UTC+8)\n\n已自動更新：\n"

    for p in proposals:
        message += f"• {p['skill_id']}: {p['title']}\n"

    send_telegram_notification(message)


def notify_minor_pending(proposals: List[Dict]) -> None:
    """通知 Minor 待執行"""
    time = get_display_time()
    message = f"⏰ Skill Evolution (Minor 待確認)\n📅 {time} (UTC+8)\n\n以下更新將在 24 小時後自動執行：\n"

    for p in proposals:
        message += f"• {p['skill_id']}: {p['title']}\n"

    message += "\n回覆「取消」可阻止執行"
    send_telegram_notification(message)


def notify_major_pending(proposals: List[Dict]) -> None:
    """通知 Major 需確認"""
    time = get_display_time()
    message = f"🔴 Skill Evolution (Major 需確認)\n📅 {time} (UTC+8)\n\n以下更新需要您的確認：\n"

    for p in proposals:
        message += f"• {p['skill_id']}: {p['title']}\n"

    message += "\n回覆「確認」執行，或「取消」放棄"
    send_telegram_notification(message)


# === 應用更新 ===

def apply_edit_change(skill_file: Path, change: Dict[str, Any]) -> bool:
    """應用編輯類型的變更（before -> after 替換）"""
    before = change.get('before', '')
    after = change.get('after', '')

    if not before or not after:
        return False

    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 檢查 before 是否存在
        if before not in content:
            print(f"    ⚠️  找不到預期內容: {before[:50]}...")
            return False

        # 執行替換
        new_content = content.replace(before, after)

        # 寫回檔案
        with open(skill_file, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True

    except Exception as e:
        print(f"    ❌ 編輯失敗: {e}")
        return False


def apply_add_change(skill_file: Path, change: Dict[str, Any]) -> bool:
    """應用新增類型的變更（在指定位置新增內容）"""
    add_content = change.get('add', '')
    section = change.get('section', '')
    after = change.get('after', '')  # 在哪個 section 之後插入
    before = change.get('before', '')  # 在哪個 section 之前插入

    if not add_content:
        return False

    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 決定插入位置
        if section == 'frontmatter':
            # 在 frontmatter 中新增
            match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
            if match:
                frontmatter = match.group(1)
                new_frontmatter = frontmatter.rstrip() + f"\n{add_content}\n"
                new_content = content.replace(match.group(0), f"---\n{new_frontmatter}---")
            else:
                return False

        elif after:
            # 在指定內容之後插入
            if after not in content:
                print(f"    ⚠️  找不到插入點: {after[:50]}...")
                return False
            new_content = content.replace(after, f"{after}\n\n{add_content}")

        elif before:
            # 在指定內容之前插入
            if before not in content:
                print(f"    ⚠️  找不到插入點: {before[:50]}...")
                return False
            new_content = content.replace(before, f"{add_content}\n\n{before}")

        else:
            # 預設：附加到檔案末尾
            new_content = content.rstrip() + f"\n\n{add_content}\n"

        # 寫回檔案
        with open(skill_file, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True

    except Exception as e:
        print(f"    ❌ 新增失敗: {e}")
        return False


def apply_proposal(proposal: Dict[str, Any], dry_run: bool = False) -> Tuple[bool, str]:
    """應用單個提案"""
    skill_name = proposal['skill_id']
    proposal_id = proposal['proposal_id']
    level = ChangeLevel(proposal['change_level'])

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}應用提案: {proposal_id}")
    print(f"  Skill: {skill_name}")
    print(f"  級別: {level.value}")
    print(f"  標題: {proposal['title']}")

    if dry_run:
        return True, "乾跑模式 - 未實際應用"

    try:
        # 1. 取得當前版本
        current_version = get_skill_version(skill_name)
        print(f"  當前版本: {current_version}")

        # 2. 備份
        backup_path = backup_skill(skill_name, current_version)
        print(f"  備份完成: {backup_path}")

        # 3. 計算新版本
        new_version = increment_version(current_version, level)
        print(f"  新版本: {new_version}")

        # 4. 應用變更
        changes = proposal.get('changes', [])
        skill_file = SKILLS_DIR / skill_name / "SKILL.md"

        for change in changes:
            change_type = change.get('type', 'review')

            if change_type == 'edit':
                # 執行字串替換
                success = apply_edit_change(skill_file, change)
                if success:
                    print(f"  ✅ 已修改: {change.get('section', 'unknown')}")
                else:
                    print(f"  ⚠️  修改失敗: {change.get('section', 'unknown')}")

            elif change_type == 'add':
                # 新增內容
                success = apply_add_change(skill_file, change)
                if success:
                    print(f"  ✅ 已新增: {change.get('section', 'unknown')}")
                else:
                    print(f"  ⚠️  新增失敗: {change.get('section', 'unknown')}")

            elif change_type == 'review':
                # review 類型只是建議，不做實際修改
                print(f"  📋 需審查: {change.get('note', '無說明')}")

        # 5. 更新版本
        update_skill_version(skill_name, new_version, proposal['title'])
        print(f"  ✅ 版本已更新")

        # 6. 更新提案狀態
        proposal['status'] = 'applied'
        proposal['applied_at'] = get_timestamp()
        proposal['backup_path'] = str(backup_path)
        save_proposal(proposal)

        # 7. 記錄到日誌
        log_evolution(skill_name, current_version, new_version, level, proposal['title'])

        return True, f"已更新到 v{new_version}"

    except Exception as e:
        return False, str(e)


def log_evolution(skill_name: str, old_version: str, new_version: str, level: ChangeLevel, description: str) -> None:
    """記錄演進歷史"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOGS_DIR / f"{today}.jsonl"

    log_entry = {
        'timestamp': get_timestamp(),
        'action': 'evolution_applied',
        'skill': skill_name,
        'version_before': old_version,
        'version_after': new_version,
        'change_level': level.value,
        'description': description
    }

    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')


# === 回滾 ===

def rollback_proposal(proposal_id: str) -> Tuple[bool, str]:
    """回滾提案"""
    proposal = load_proposal(proposal_id)
    if not proposal:
        return False, f"提案不存在: {proposal_id}"

    if proposal.get('status') != 'applied':
        return False, f"提案狀態不是 applied: {proposal.get('status')}"

    backup_path = proposal.get('backup_path')
    if not backup_path:
        return False, "沒有備份路徑"

    backup_file = Path(backup_path)
    if not backup_file.exists():
        return False, f"備份檔案不存在: {backup_path}"

    skill_name = proposal['skill_id']

    # 還原備份
    if restore_skill(skill_name, backup_file):
        # 更新提案狀態
        proposal['status'] = 'rolled_back'
        proposal['rolled_back_at'] = get_timestamp()
        save_proposal(proposal)

        return True, f"已回滾 {skill_name}"
    else:
        return False, "還原失敗"


# === 主程式 ===

def main():
    parser = argparse.ArgumentParser(
        description='Skill Evolution - 更新應用腳本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python3 apply-update.py                          # 互動模式
  python3 apply-update.py --level patch            # 自動應用 patch 級別
  python3 apply-update.py --level minor --confirm  # 應用 minor 級別（需確認）
  python3 apply-update.py --all --confirm          # 應用所有
  python3 apply-update.py --proposal ID            # 應用特定提案
  python3 apply-update.py --rollback ID            # 回滾特定提案
  python3 apply-update.py --list                   # 列出待處理提案
  python3 apply-update.py --dry-run                # 乾跑模式
        """
    )

    parser.add_argument('--level', type=str, choices=['patch', 'minor', 'major'],
                        help='應用指定級別的提案')
    parser.add_argument('--proposal', type=str, help='應用特定提案 ID')
    parser.add_argument('--rollback', type=str, help='回滾特定提案 ID')
    parser.add_argument('--all', action='store_true', help='應用所有待處理提案')
    parser.add_argument('--confirm', action='store_true', help='確認執行（用於 minor/major）')
    parser.add_argument('--list', action='store_true', help='列出待處理提案')
    parser.add_argument('--dry-run', action='store_true', help='乾跑模式')
    parser.add_argument('--notify', action='store_true', help='發送通知')

    args = parser.parse_args()

    print("🔄 Skill Evolution 更新應用器")
    print()

    # 確保目錄存在
    for d in [LOGS_DIR, PENDING_DIR, REPORTS_DIR, BACKUPS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # 列出待處理提案
    if args.list:
        proposals = list_pending_proposals()
        if not proposals:
            print("📭 沒有待處理的提案")
            return

        print(f"📋 待處理提案 ({len(proposals)} 個):\n")
        for p in proposals:
            level_emoji = {'patch': '🟢', 'minor': '🟡', 'major': '🔴'}.get(p['change_level'], '⚪')
            print(f"  {level_emoji} {p['proposal_id']}")
            print(f"     Skill: {p['skill_id']}")
            print(f"     標題: {p['title']}")
            print(f"     建立: {p['created_at'][:10]}")
            print()
        return

    # 回滾
    if args.rollback:
        success, message = rollback_proposal(args.rollback)
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
        return

    # 應用特定提案
    if args.proposal:
        proposal = load_proposal(args.proposal)
        if not proposal:
            print(f"❌ 提案不存在: {args.proposal}")
            return

        success, message = apply_proposal(proposal, args.dry_run)
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
        return

    # 取得待處理提案
    proposals = list_pending_proposals()
    if not proposals:
        print("📭 沒有待處理的提案")
        return

    # 按級別分類
    by_level = {
        'patch': [],
        'minor': [],
        'major': []
    }
    for p in proposals:
        level = p.get('change_level', 'minor')
        if level in by_level:
            by_level[level].append(p)

    print(f"📊 待處理提案: 🟢 {len(by_level['patch'])} patch | 🟡 {len(by_level['minor'])} minor | 🔴 {len(by_level['major'])} major")
    print()

    # 應用指定級別
    if args.level:
        level = args.level
        to_apply = by_level.get(level, [])

        if not to_apply:
            print(f"📭 沒有 {level} 級別的提案")
            return

        # major 和 minor 需要確認
        if level in ['major', 'minor'] and not args.confirm:
            print(f"⚠️  {level} 級別需要使用 --confirm 確認")

            if args.notify:
                if level == 'major':
                    notify_major_pending(to_apply)
                else:
                    notify_minor_pending(to_apply)
                print("📤 已發送通知")
            return

        applied = []
        failed = []

        for p in to_apply:
            success, message = apply_proposal(p, args.dry_run)
            if success:
                applied.append(p)
                print(f"  ✅ {p['proposal_id']}: {message}")
            else:
                failed.append((p, message))
                print(f"  ❌ {p['proposal_id']}: {message}")

        print()
        print(f"📊 結果: {len(applied)} 成功, {len(failed)} 失敗")

        # 發送通知
        if args.notify and applied and level == 'patch':
            notify_patch_applied(applied)
            print("📤 已發送通知")

        return

    # 應用所有（需確認）
    if args.all:
        if not args.confirm:
            print("⚠️  應用所有提案需要使用 --confirm 確認")
            return

        applied = []
        failed = []

        for level in ['patch', 'minor', 'major']:
            for p in by_level[level]:
                success, message = apply_proposal(p, args.dry_run)
                if success:
                    applied.append(p)
                    print(f"  ✅ {p['proposal_id']}: {message}")
                else:
                    failed.append((p, message))
                    print(f"  ❌ {p['proposal_id']}: {message}")

        print()
        print(f"📊 結果: {len(applied)} 成功, {len(failed)} 失敗")
        return

    # 互動模式
    print("📋 互動模式")
    print()
    print("可用命令:")
    print("  --list              列出待處理提案")
    print("  --level patch       自動應用 patch 級別")
    print("  --proposal ID       應用特定提案")
    print("  --rollback ID       回滾特定提案")
    print()


if __name__ == "__main__":
    main()
