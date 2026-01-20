#!/bin/bash
# ============================================================
# Skill Evolution - 數據收集腳本
#
# 用途：在 session 結束時收集 skill 使用數據
# 觸發：SessionEnd hook 或手動執行
#
# 使用方式：
#   ./collect-session-data.sh              # 正常執行
#   ./collect-session-data.sh test         # 測試模式
#   ./collect-session-data.sh --help       # 顯示幫助
# ============================================================

set -euo pipefail

# === 配置 ===
EVOLUTION_DIR="$HOME/.claude/evolution"
LOGS_DIR="$EVOLUTION_DIR/logs"
SKILLS_DIR="$HOME/.claude/skills"
TODAY=$(TZ='Asia/Taipei' date '+%Y-%m-%d')
TIMESTAMP=$(TZ='Asia/Taipei' date '+%Y-%m-%dT%H:%M:%S+08:00')
LOG_FILE="$LOGS_DIR/$TODAY.jsonl"

# === 顏色輸出 ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# === 函數 ===

show_help() {
    cat << EOF
Skill Evolution - 數據收集腳本

用法：
  $0              正常執行，收集 session 數據
  $0 test         測試模式，不寫入實際日誌
  $0 --help       顯示此幫助訊息

說明：
  此腳本在 Claude session 結束時被 SessionEnd hook 調用，
  收集當次 session 中的 skill 使用數據。

數據來源：
  1. 環境變數（由 Claude 傳入）
  2. 最近的 session 日誌
  3. claude-mem 記憶

輸出位置：
  $LOGS_DIR/YYYY-MM-DD.jsonl

EOF
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

ensure_directories() {
    mkdir -p "$LOGS_DIR"
    mkdir -p "$EVOLUTION_DIR/pending"
    mkdir -p "$EVOLUTION_DIR/reports"
    mkdir -p "$EVOLUTION_DIR/backups"
}

# 從環境變數獲取 session 信息
get_session_info() {
    local session_id="${CLAUDE_SESSION_ID:-unknown}"
    local session_cwd="${CLAUDE_CWD:-$HOME}"
    local tool_name="${TOOL_NAME:-}"
    local tool_input="${TOOL_INPUT:-}"

    echo "{\"session_id\": \"$session_id\", \"cwd\": \"$session_cwd\"}"
}

# 解析最近的 skill 調用
# 從 claude-mem 或 session 環境變數中提取
collect_skill_invocations() {
    local session_info="$1"
    local session_id=$(echo "$session_info" | jq -r '.session_id')

    # 檢查是否有 skill 相關的環境變數
    if [[ -n "${SKILL_INVOKED:-}" ]]; then
        local skill_name="$SKILL_INVOKED"
        local skill_result="${SKILL_RESULT:-success}"
        local skill_duration="${SKILL_DURATION:-0}"

        # 寫入日誌
        local log_entry=$(jq -n \
            --arg ts "$TIMESTAMP" \
            --arg sid "$session_id" \
            --arg skill "$skill_name" \
            --arg action "invoked" \
            --arg result "$skill_result" \
            --argjson duration "$skill_duration" \
            '{
                timestamp: $ts,
                session_id: $sid,
                skill: $skill,
                action: $action,
                result: $result,
                duration_ms: $duration
            }')

        echo "$log_entry"
    fi
}

# 從 .claude/projects 解析最近的 session 數據
parse_recent_sessions() {
    local projects_dir="$HOME/.claude/projects"

    if [[ ! -d "$projects_dir" ]]; then
        log_warn "Projects 目錄不存在: $projects_dir"
        return
    fi

    # 找出最近 1 小時內修改的 .jsonl 檔案
    find "$projects_dir" -name "*.jsonl" -mmin -60 2>/dev/null | while read -r session_file; do
        if [[ ! -f "$session_file" ]]; then
            continue
        fi

        # 解析 JSONL 檔案中的 skill 調用
        while IFS= read -r line; do
            # 跳過空行
            [[ -z "$line" ]] && continue

            # 檢查是否有 Skill tool 調用
            local has_skill_tool=$(echo "$line" | jq -r 'select(.content[]?.type == "tool_use" and .content[]?.name == "Skill") | .content[] | select(.type == "tool_use") | .name' 2>/dev/null)

            if [[ "$has_skill_tool" == "Skill" ]]; then
                # 提取 skill 名稱
                local skill_name=$(echo "$line" | jq -r '.content[] | select(.type == "tool_use" and .name == "Skill") | .input.skill' 2>/dev/null)

                if [[ -n "$skill_name" ]]; then
                    # 從檔案內容判斷結果（簡化：假設有回應就是成功）
                    local result="success"

                    local log_entry=$(jq -n \
                        --arg ts "$TIMESTAMP" \
                        --arg skill "$skill_name" \
                        --arg action "invoked" \
                        --arg result "$result" \
                        --arg source "session-log" \
                        '{
                            timestamp: $ts,
                            skill: $skill,
                            action: $action,
                            result: $result,
                            source: $source
                        }')

                    echo "$log_entry"
                fi
            fi
        done < "$session_file"
    done
}

# 掃描 skills 目錄，記錄 skill 清單快照
snapshot_skills() {
    local skills=()

    for skill_dir in "$SKILLS_DIR"/*/; do
        if [[ -f "${skill_dir}SKILL.md" ]]; then
            local skill_name=$(basename "$skill_dir")

            # 跳過特殊目錄
            if [[ "$skill_name" == "_archived" || "$skill_name" == "_shared" ]]; then
                continue
            fi

            # 檢查是否有 evolution metadata
            local has_evolution=$(grep -l "evolution:" "${skill_dir}SKILL.md" 2>/dev/null && echo "true" || echo "false")

            skills+=("$skill_name")
        fi
    done

    # 輸出 skills 清單
    local snapshot=$(jq -n \
        --arg ts "$TIMESTAMP" \
        --arg action "snapshot" \
        --argjson count "${#skills[@]}" \
        --argjson skills "$(printf '%s\n' "${skills[@]}" | jq -R . | jq -s .)" \
        '{
            timestamp: $ts,
            action: $action,
            skill_count: $count,
            skills: $skills
        }')

    echo "$snapshot"
}

# 主執行函數
main() {
    local mode="${1:-normal}"

    case "$mode" in
        --help|-h)
            show_help
            exit 0
            ;;
        test)
            log_info "測試模式 - 不寫入實際日誌"

            ensure_directories

            log_info "收集 session 信息..."
            local session_info=$(get_session_info)
            echo "Session Info: $session_info"

            log_info "掃描 skills..."
            local snapshot=$(snapshot_skills)
            echo "Snapshot: $snapshot"

            log_success "測試完成"
            exit 0
            ;;
        normal|*)
            # 正常執行
            ensure_directories

            log_info "開始收集 session 數據..."

            # 收集 session 信息
            local session_info=$(get_session_info)

            # 收集 skill 調用
            local invocations=$(collect_skill_invocations "$session_info")

            # 如果有調用記錄，寫入日誌
            if [[ -n "$invocations" ]]; then
                echo "$invocations" >> "$LOG_FILE"
                log_success "已記錄 skill 調用"
            fi

            # 解析最近 sessions
            local recent_data=$(parse_recent_sessions)
            if [[ -n "$recent_data" ]]; then
                echo "$recent_data" >> "$LOG_FILE"
            fi

            # 每天第一次執行時，記錄 skills 快照
            local snapshot_marker="$LOGS_DIR/.snapshot-$TODAY"
            if [[ ! -f "$snapshot_marker" ]]; then
                local snapshot=$(snapshot_skills)
                echo "$snapshot" >> "$LOG_FILE"
                touch "$snapshot_marker"
                log_info "已建立今日 skills 快照"
            fi

            log_success "數據收集完成: $LOG_FILE"
            ;;
    esac
}

# === 執行 ===
main "$@"
