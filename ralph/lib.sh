#!/usr/bin/env bash
RALPH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$RALPH_DIR/.." && pwd)"
ISSUES_DIR="${RALPH_ISSUES_DIR:-$REPO_ROOT/issues}"
ISSUES_SOURCE="${RALPH_ISSUES_SOURCE:-auto}"

color_llm_out() {
	[[ -t 1 && -z "${NO_COLOR:-}" ]] || { cat; return; }
	local cols w=0 c chunk i len
	cols=$(tput cols 2>/dev/null) || cols=80
	cols=$((cols > 1 ? cols : 80))
	printf '\033[1;36m'
	while IFS= read -r -n 4096 chunk || [[ -n "$chunk" ]]; do
		printf '\033[1;36m'
		len=${#chunk}
		for ((i = 0; i < len; i++)); do
			c=${chunk:i:1}
			case "$c" in
				$'\n') printf '\n'; w=0 ;;
				$'\r') ;;
				' ')
					if (( w + 1 >= cols )); then printf '\n '; w=1
					else printf ' '; ((w++)); fi
					;;
				*)
					if (( w + 1 > cols )); then printf '\n%s' "$c"; w=1
					else printf '%s' "$c"; ((w++)); fi
					;;
			esac
		done
	done
	printf '\033[0m\n'
}

issues_backend() {
	case "$ISSUES_SOURCE" in
		local|folder) echo local ;;
		github|gh) echo github ;;
		auto)
			if [[ -d "$ISSUES_DIR" ]]; then echo local
			elif command -v gh >/dev/null 2>&1; then echo github
			else echo local
			fi
			;;
		*) echo "unknown RALPH_ISSUES_SOURCE: $ISSUES_SOURCE" >&2; return 1 ;;
	esac
}

local_issue_files() {
	[[ -d "$ISSUES_DIR" ]] || return 0
	find "$ISSUES_DIR" -type f \( -name meta.md -o -path '*/tasks/*.md' \) ! -path '*/README.md' 2>/dev/null | sort
}

local_frontmatter() {
	awk '/^---$/{if(++n==1)next; if(n==2)exit} n==1' "$1" 2>/dev/null
}

local_is_ready() {
	local f=$1 fm
	[[ -f "$f" ]] || return 1
	fm=$(local_frontmatter "$f")
	[[ -n "$fm" ]] || return 1
	echo "$fm" | grep -qiE '^status:[[:space:]]*closed' && return 1
	echo "$fm" | grep -qE '(^labels:.*ready-for-agent|[[:space:]-]ready-for-agent|^status:[[:space:]]*ready-for-agent)' || return 1
}

local_issue_id() {
	local f=$1 fm id
	fm=$(local_frontmatter "$f")
	id=$(sed -n 's/^id:[[:space:]]*"\?\([^"]*\)"\?.*/\1/p' <<<"$fm" | head -1)
	if [[ -n "$id" ]]; then printf '%s' "$id"
	else basename "$(dirname "$f")" | sed -E 's/^([0-9]+).*/\1/; t; s/.*/?/'
	fi
}

local_issue_title() {
	local f=$1 fm title
	fm=$(local_frontmatter "$f")
	title=$(sed -n 's/^title:[[:space:]]*"\?\(.*\)"\?.*/\1/p' <<<"$fm" | head -1)
	if [[ -n "$title" ]]; then printf '%s' "$title"
	else sed -n 's/^#\+[[:space:]]*//p' "$f" | head -1
	fi
}

format_local_issue() {
	local f=$1 rel id title body
	rel=${f#"$REPO_ROOT/"}
	id=$(local_issue_id "$f")
	title=$(local_issue_title "$f")
	body=$(awk '/^---$/{if(++n==1){skip=1;next} if(n==2){skip=0;next}} !skip' "$f")
	printf '# Issue %s: %s\n\nPath: %s\n\n%s\n\n---\n' "${id:-?}" "${title:-(untitled)}" "$rel" "$body"
}

count_issues_local() {
	local f n=0
	while IFS= read -r f; do
		[[ -n "$f" ]] || continue
		local_is_ready "$f" && ((n++)) || true
	done < <(local_issue_files)
	echo "$n"
}

fetch_issues_local() {
	local f out= found=0
	while IFS= read -r f; do
		[[ -n "$f" ]] || continue
		local_is_ready "$f" || continue
		found=1
		format_local_issue "$f"
	done < <(local_issue_files)
	(( found )) || echo "No ready-for-agent issues found in $ISSUES_DIR"
}

count_issues_github() {
	gh issue list --state open --label ready-for-agent --json number --jq 'length' 2>/dev/null || echo 0
}

fetch_issues_github() {
	gh issue list --state open --label ready-for-agent \
		--json number,title,body,labels \
		--jq '.[] | "# Issue #\(.number): \(.title)\n\n\(.body)\n\n---"' 2>/dev/null \
		|| echo "No ready-for-agent issues found"
}

count_issues() {
	case "$(issues_backend)" in
		local) count_issues_local ;;
		github) count_issues_github ;;
	esac
}

fetch_issues() {
	case "$(issues_backend)" in
		local) fetch_issues_local ;;
		github) fetch_issues_github ;;
	esac
}

fetch_commits() {
	git -C "$REPO_ROOT" log -n 5 --format="%H%n%ad%n%B---" --date=short 2>/dev/null \
		|| echo "No commits found"
}

build_context() {
	local priority_hint=${1:-} commits issues prompt backend
	backend=$(issues_backend)
	commits=$(fetch_commits)
	issues=$(fetch_issues)
	prompt=$(cat "$RALPH_DIR/prompt.md")
	if [[ -n "$priority_hint" ]]; then
		printf 'Issue source: %s\n\nPrevious commits:\n%s\n\nOpen issues (ready-for-agent):\n%s\n\n# PREFERRED ORDER (operator)\n\n%s\n\n%s' \
			"$backend" "$commits" "$issues" "$priority_hint" "$prompt"
	else
		printf 'Issue source: %s\n\nPrevious commits:\n%s\n\nOpen issues (ready-for-agent):\n%s\n\n%s' \
			"$backend" "$commits" "$issues" "$prompt"
	fi
}
