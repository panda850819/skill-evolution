#!/bin/bash
# ============================================================
# Skill Evolution - 基礎測試
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURES_DIR="$SCRIPT_DIR/fixtures"
TEMP_DIR="$SCRIPT_DIR/temp"

# 顏色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

# === 輔助函數 ===

pass() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

setup() {
    echo "Setting up test environment..."
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR/skills/test-skill"
    mkdir -p "$TEMP_DIR/evolution/logs"
    mkdir -p "$TEMP_DIR/evolution/pending"
    mkdir -p "$TEMP_DIR/evolution/backups"
}

cleanup() {
    echo "Cleaning up..."
    rm -rf "$TEMP_DIR"
}

# === 測試 ===

test_fixture_files() {
    echo ""
    echo "Test 1: Fixture files exist"

    [[ -f "$FIXTURES_DIR/sample_skill.md" ]] || fail "sample_skill.md missing"
    pass "sample_skill.md exists"

    [[ -f "$FIXTURES_DIR/sample_logs.jsonl" ]] || fail "sample_logs.jsonl missing"
    pass "sample_logs.jsonl exists"

    [[ -f "$FIXTURES_DIR/sample_proposal.yaml" ]] || fail "sample_proposal.yaml missing"
    pass "sample_proposal.yaml exists"
}

test_skill_file_parsing() {
    echo ""
    echo "Test 2: Skill file parsing"

    # 檢查是否可以解析 frontmatter
    local has_name=$(grep -q "^name: test-skill" "$FIXTURES_DIR/sample_skill.md" && echo "true" || echo "false")
    [[ "$has_name" == "true" ]] || fail "Cannot parse skill name"
    pass "Can parse skill name"

    local has_version=$(grep -q "version: \"1.0.0\"" "$FIXTURES_DIR/sample_skill.md" && echo "true" || echo "false")
    [[ "$has_version" == "true" ]] || fail "Cannot parse version"
    pass "Can parse version"
}

test_logs_parsing() {
    echo ""
    echo "Test 3: Logs parsing"

    # 檢查 logs 可以被 jq 解析
    local line_count=$(wc -l < "$FIXTURES_DIR/sample_logs.jsonl" | tr -d ' ')
    [[ "$line_count" -eq "5" ]] || fail "Expected 5 log lines, got $line_count"
    pass "Log file has correct line count"

    # 解析第一行
    local first_line=$(head -n1 "$FIXTURES_DIR/sample_logs.jsonl")
    local skill_name=$(echo "$first_line" | jq -r '.skill')
    [[ "$skill_name" == "test-skill" ]] || fail "Cannot parse skill name from log"
    pass "Can parse skill name from log"
}

test_proposal_parsing() {
    echo ""
    echo "Test 4: Proposal parsing"

    # 檢查 proposal 可以被 yq/python yaml 解析
    local proposal_id=$(grep "^proposal_id:" "$FIXTURES_DIR/sample_proposal.yaml" | cut -d: -f2 | tr -d ' ')
    [[ "$proposal_id" == "test-skill-abc123" ]] || fail "Cannot parse proposal_id"
    pass "Can parse proposal_id"

    local change_level=$(grep "^change_level:" "$FIXTURES_DIR/sample_proposal.yaml" | cut -d: -f2 | tr -d ' ')
    [[ "$change_level" == "patch" ]] || fail "Cannot parse change_level"
    pass "Can parse change_level"
}

test_collect_script_exists() {
    echo ""
    echo "Test 5: Scripts exist and are executable"

    local collect_script="../scripts/collect-session-data.sh"
    [[ -f "$collect_script" ]] || fail "collect-session-data.sh not found"
    [[ -x "$collect_script" ]] || fail "collect-session-data.sh not executable"
    pass "collect-session-data.sh exists and is executable"
}

test_analyze_script_exists() {
    echo ""
    echo "Test 6: Python scripts exist"

    local analyze_script="../scripts/analyze-opportunities.py"
    [[ -f "$analyze_script" ]] || fail "analyze-opportunities.py not found"
    pass "analyze-opportunities.py exists"

    local apply_script="../scripts/apply-update.py"
    [[ -f "$apply_script" ]] || fail "apply-update.py not found"
    pass "apply-update.py exists"
}

# === 運行測試 ===

main() {
    echo "============================================"
    echo "Skill Evolution - Basic Tests"
    echo "============================================"

    setup

    test_fixture_files
    test_skill_file_parsing
    test_logs_parsing
    test_proposal_parsing
    test_collect_script_exists
    test_analyze_script_exists

    echo ""
    echo "============================================"
    echo -e "${GREEN}All tests passed!${NC}"
    echo "============================================"

    cleanup
}

main "$@"
