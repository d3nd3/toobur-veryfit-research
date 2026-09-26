#!/usr/bin/env bash
set -eo pipefail
source "$(dirname "$0")/lib.sh"

log() { printf '\n' >&2; echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >&2; }

LOCK_DIR=/tmp/ralph-afk.lock
BG_PIDS=()
tmpfile=

on_exit() {
	cleanup_bg
	[[ -n "$tmpfile" ]] && rm -f "$tmpfile"
	rmdir "$LOCK_DIR" 2>/dev/null || true
}

cleanup_bg() {
	local pid
	for pid in "${BG_PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
	for pid in "${BG_PIDS[@]}"; do wait "$pid" 2>/dev/null || true; done
	BG_PIDS=()
}

stop_bg() {
	local pid
	for pid in "$@"; do kill "$pid" 2>/dev/null || true; done
	sleep 0.1
	for pid in "$@"; do kill -9 "$pid" 2>/dev/null || true; done
	for pid in "$@"; do wait "$pid" 2>/dev/null || true; done
}

log_agent_event() {
	while IFS= read -r line; do
		printf '%s\n' "$line"
		type=$(jq -r '.type // empty' <<<"$line" 2>/dev/null) || continue
		case "$type" in
			system)
				[[ $(jq -r '.subtype // empty' <<<"$line") == init ]] &&
					log "agent: init model=$(jq -r '.model // "?"' <<<"$line")"
				;;
			tool_call)
				sub=$(jq -r '.subtype // empty' <<<"$line")
				if [[ "$sub" == started ]]; then
					tool=$(jq -r '.tool_call | keys[0] // "tool"' <<<"$line")
					path=$(jq -r '.tool_call.readToolCall.args.path // .tool_call.writeToolCall.args.path // empty' <<<"$line")
					log "agent: $tool started${path:+ path=$path}"
				elif [[ "$sub" == completed ]]; then
					log "agent: tool completed"
				fi
				;;
			result) log "agent: finished duration=$(jq -r '.duration_ms // "?"' <<<"$line")ms" ;;
		esac
	done
}

watch_debug_log() {
	local iter=$1
	for _ in $(seq 1 60); do
		local d
		d=$(ls -td /tmp/cursor-agent-debug-* 2>/dev/null | head -1) || { sleep 1; continue; }
		[[ -f "$d/session.log" ]] || { sleep 1; continue; }
		log "iteration $iter: cursor debug log $d/session.log"
		return
	done
}

priority_hint=""
if [[ -n "${1:-}" ]]; then
	if [[ "$1" =~ ^[0-9]+$ ]]; then
		iterations=$1
		priority_hint=${2:-}
	else
		iterations=$(count_issues)
		priority_hint=$1
		log "no iteration count specified — using $iterations (one per ready-for-agent issue)"
	fi
else
	iterations=$(count_issues)
	log "no iteration count specified — using $iterations (one per ready-for-agent issue)"
fi

if [ "$iterations" -eq 0 ]; then
	log "no ready-for-agent issues; nothing to do"
	exit 0
fi

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
	log "another afk.sh is already running (lock: $LOCK_DIR) — refusing to start"
	exit 1
fi
trap on_exit EXIT

log "afk.sh starting ($iterations iteration(s))${priority_hint:+ — priority: $priority_hint}"

stream_text='select(.type == "assistant").message.content[]? | select(.type == "text").text // empty | . + "\n\n"'
final_result='select(.type == "result").result // empty'

for ((i = 1; i <= iterations; i++)); do
	iter_start=$(date +%s)
	log "iteration $i/$iterations: begin"

	tmpfile=$(mktemp)

	log "iteration $i/$iterations: fetching context (git log + issues)..."
	ctx_start=$(date +%s)
	context=$(build_context "$priority_hint")
	log "iteration $i/$iterations: context ready (${#context} bytes, $(( $(date +%s) - ctx_start ))s)"

	log "iteration $i/$iterations: starting agent stream (--debug)..."
	agent_start=$(date +%s)
	iter=$i iter_total=$iterations iter_agent_start=$agent_start
	(
		while sleep 30; do
			log "iteration $iter/$iter_total: agent still running ($(( $(date +%s) - iter_agent_start ))s elapsed, no stream end yet)"
		done
	) &
	heartbeat_pid=$!
	BG_PIDS+=("$heartbeat_pid")
	watch_debug_log "$i" &
	debug_watch_pid=$!
	BG_PIDS+=("$debug_watch_pid")

	# Capture to tmpfile even if the display pipe (jq/color_llm_out) breaks (EPIPE).
	set +e
	agent --debug -p --trust --force --output-format stream-json "$context" \
		| grep --line-buffered '^{' \
		| tee --output-error=exit-nopipe "$tmpfile" \
		| log_agent_event \
		| jq --unbuffered -rj "$stream_text" | color_llm_out
	pipe_rc=$?
	agent_rc=${PIPESTATUS[0]}
	set -e

	stop_bg "$heartbeat_pid" "$debug_watch_pid"
	BG_PIDS=()
	if (( agent_rc != 0 )); then
		log "iteration $i/$iterations: warning — agent exited $agent_rc"
	elif (( pipe_rc != 0 )); then
		log "iteration $i/$iterations: warning — display pipeline failed (exit $pipe_rc); parsing captured stream anyway"
	fi
	log "iteration $i/$iterations: agent stream finished ($(( $(date +%s) - agent_start ))s)"
	d=$(ls -td /tmp/cursor-agent-debug-* 2>/dev/null | head -1)
	[[ -n "$d" && -f "$d/session.log" ]] && log "iteration $i/$iterations: debug log $d/session.log"

	log "iteration $i/$iterations: parsing result from $tmpfile..."
	result=$(jq -r "$final_result" "$tmpfile")
	if [ -z "$result" ]; then
		log "iteration $i/$iterations: warning — empty result (check debug log above)"
	else
		log "iteration $i/$iterations: result parsed (${#result} chars)"
	fi

	log "iteration $i/$iterations: done ($(( $(date +%s) - iter_start ))s total)"
	rm -f "$tmpfile"
	tmpfile=

	if [[ "$result" == *" NO MORE TASKS "* ]]; then
		log "Ralph complete after $i iterations."
		exit 0
	fi

	(( i < iterations )) && log "iteration $i/$iterations: proceeding to next iteration"
done

log "afk.sh finished all $iterations iteration(s) without completion signal"
