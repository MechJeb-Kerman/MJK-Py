#!/usr/bin/env bash
# =============================================================================
#  自动同步（智能批量）—— 由 install/cloud-setup.sh 生成
#
#  模式（写在 sync.conf 里，命令行可临时覆盖）：
#    idle      默认：静默 idle_seconds 没有新改动才提交；一直在改也会在 max_wait 后兜底提交
#    interval  每 interval 秒提交一次（旧行为）
#    manual    永不自动提交，只在你手动 --now 时提交
#
#    bash sync.sh --status          看模式 / 待提交的改动 / 最近提交
#    bash sync.sh --plan            只显示"会提交什么、提交信息是什么"，不动 git 历史
#    bash sync.sh --now             立刻提交一次
#    bash sync.sh --mode=interval --interval=300 --enable   切换并写回 sync.conf
#    bash sync.sh --disable         暂停自动同步（改动仍然留在工作区）
#    bash sync.sh --message="feat: 给面板加额度条"   指定下一次提交信息
# =============================================================================
set -u
CLOUD_DIR="/workspaces/MJK-Py/.dsh-cloud"
BRANCH="main"
WORKSPACE_DIR="${DSH_WORKSPACE:-$HOME/dsh-workspace}"
CONF="$CLOUD_DIR/sync.conf"
STATE="$HOME/.dsh-sync-state"
LOG="$HOME/dsh-sync.log"

enabled=on
mode=idle
idle_seconds=600
max_wait=1800
interval=300
tick=30
prefix=dsh
squash_window_seconds=0
MODE_OVERRIDE=""; IDLE_OVERRIDE=""; INT_OVERRIDE=""; ENABLE_OVERRIDE=""; MESSAGE_OVERRIDE=""
SQUASH_OVERRIDE=""
FP=""; CHANGED_AT=""; FIRST_AT=""; LAST_COMMIT_AT=""

usage() {
  sed -n '3,20p' "$0" 2>/dev/null | sed 's/^# \{0,1\}//' ||
    echo "用法：bash sync.sh [--daemon|--status|--plan|--now|--help]"
}

load_conf() {
  [ -f "$CONF" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"
    case "$line" in *=*) ;; *) continue ;; esac
    key="$(printf '%s' "${line%%=*}" | tr -d ' \t')"
    val="$(printf '%s' "${line#*=}" | tr -d ' \t"' | tr -d "'")"
    case "$key" in
      enabled) enabled="$val" ;;
      mode) mode="$val" ;;
      idle_seconds) idle_seconds="$val" ;;
      max_wait) max_wait="$val" ;;
      interval) interval="$val" ;;
      tick) tick="$val" ;;
      prefix) prefix="$val" ;;
      squash_window_seconds) squash_window_seconds="$val" ;;
    esac
  done < "$CONF"
}

save_conf() {
  [ -f "$CONF" ] || return 0
  tmp="$CONF.tmp"
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      enabled=*)      printf 'enabled=%s\n' "$enabled" ;;
      mode=*)         printf 'mode=%s\n' "$mode" ;;
      idle_seconds=*) printf 'idle_seconds=%s\n' "$idle_seconds" ;;
      max_wait=*)     printf 'max_wait=%s\n' "$max_wait" ;;
      interval=*)     printf 'interval=%s\n' "$interval" ;;
      tick=*)         printf 'tick=%s\n' "$tick" ;;
      prefix=*)       printf 'prefix=%s\n' "$prefix" ;;
      squash_window_seconds=*) printf 'squash_window_seconds=%s\n' "$squash_window_seconds" ;;
      *)              printf '%s\n' "$line" ;;
    esac
  done < "$CONF" > "$tmp"
  # 老版本 sync.conf 里没有新键时补上（否则 --squash-window=… 会悄悄不生效）
  for kv in "enabled=$enabled" "mode=$mode" "idle_seconds=$idle_seconds" "max_wait=$max_wait" \
            "interval=$interval" "tick=$tick" "prefix=$prefix" \
            "squash_window_seconds=$squash_window_seconds"; do
    grep -q "^${kv%%=*}=" "$tmp" || printf '%s\n' "$kv" >> "$tmp"
  done
  mv "$tmp" "$CONF"
}

load_state() {
  [ -f "$STATE" ] || return 0
  # shellcheck disable=SC1090
  . "$STATE"
}

save_state() {
  {
    printf 'FP=%q\n' "$FP"
    printf 'CHANGED_AT=%q\n' "$CHANGED_AT"
    printf 'FIRST_AT=%q\n' "$FIRST_AT"
    printf 'LAST_COMMIT_AT=%q\n' "$LAST_COMMIT_AT"
  } > "$STATE"
}

now_epoch() { date +%s; }

keep_empty_dirs() {
  find "$WORKSPACE_DIR" \( -name .git -o -name node_modules \) -prune -o -type d -empty -print0 2>/dev/null |
    while IFS= read -r -d '' d; do
      rel="${d#"$WORKSPACE_DIR"/}"
      git -C "$WORKSPACE_DIR" check-ignore -q -- "$rel" || : >"$d/.gitkeep"
    done
}

# 指纹：已跟踪文件的 diff + 未跟踪文件的大小/改动时间 —— 一点点改动都能看出来
fingerprint() {
  {
    git -C "$WORKSPACE_DIR" status --porcelain -uall 2>/dev/null
    git -C "$WORKSPACE_DIR" diff --binary 2>/dev/null
    git -C "$WORKSPACE_DIR" ls-files --others --exclude-standard -z 2>/dev/null |
      xargs -0 -r stat -c '%n %s %Y' 2>/dev/null
  } | sha1sum | cut -d' ' -f1
}

dirty() { [ -n "$(git -C "$WORKSPACE_DIR" status --porcelain 2>/dev/null)" ]; }

# 提交信息：优先用 AI/人 留下的提示文件，否则按改动内容自动生成
build_message() {
  for hint in "$CLOUD_DIR/commit-msg" "$WORKSPACE_DIR/.dsh-commit-msg"; do
    if [ -s "$hint" ]; then
      head -1 "$hint" | cut -c1-200
      rm -f "$hint"
      return 0
    fi
  done
  added="$(git -C "$WORKSPACE_DIR" diff --cached --name-status 2>/dev/null | awk '$1=="A"{c++} END{print c+0}')"
  deleted="$(git -C "$WORKSPACE_DIR" diff --cached --name-status 2>/dev/null | awk '$1=="D"{c++} END{print c+0}')"
  total="$(git -C "$WORKSPACE_DIR" diff --cached --name-only 2>/dev/null | grep -c . || true)"
  verb=update
  if [ "${deleted:-0}" -gt 0 ] && [ "${added:-0}" -eq 0 ]; then
    verb=remove
  elif [ "${added:-0}" -gt 0 ] && [ "${added:-0}" = "${total:-1}" ]; then
    verb=add
  fi
  dirs="$(git -C "$WORKSPACE_DIR" diff --cached --name-only -z 2>/dev/null | tr '\0' '\n' |
    tr -d '"' | awk -F/ 'NF>1{print $1"/"$2} NF==1{print $1}' | sort | uniq -c | sort -rn |
    head -3 | awk '{print $2}' | paste -sd', ' -)"
  [ -n "$dirs" ] || dirs="workspace"
  printf '%s: %s %s (%s files)' "$prefix" "$verb" "$dirs" "${total:-0}"
}

commit_now() {
  cd "$WORKSPACE_DIR" || return 1
  keep_empty_dirs
  if ! dirty; then
    echo "没有待提交的改动"
    return 0
  fi
  was_staged=0
  git diff --cached --quiet || was_staged=1
  git add -A
  MSG="$(build_message)"
  if [ "$PLAN_ONLY" = 1 ]; then
    echo "提交信息：$MSG"
    echo "涉及文件："
    git diff --cached --name-status | head -20 | sed 's/^/  /'
    [ "$was_staged" = 0 ] && git reset -q
    return 0
  fi
  BODY="$(git diff --cached --name-only -z | tr '\0' '\n' | sed '/^$/d' | head -20 | paste -sd', ' -)"
  # 折叠窗口：上一条也是自动提交、且够新 → 把改动并进去（改写那一条）
  LAST_SUBJ="$(git log -1 --format=%s 2>/dev/null || echo '')"
  LAST_TS="$(git log -1 --format=%ct 2>/dev/null || echo 0)"
  if [ "${squash_window_seconds:-0}" -gt 0 ] && [ -n "$LAST_SUBJ" ]; then
    case "$LAST_SUBJ" in
      "$prefix: "*)
        if [ $(( $(now_epoch) - LAST_TS )) -le "$squash_window_seconds" ]; then
          PRE_FOLD="$(git rev-parse HEAD)"
          if git -c user.name="dsh cloud" -c user.email="dsh-cloud@users.noreply.github.com" \
               commit -q --amend -m "$MSG" ${BODY:+-m "$BODY"} >>"$LOG" 2>&1; then
            if git push -q --force-with-lease origin "HEAD:$BRANCH" >>"$LOG" 2>&1; then
              echo "$(date -Is) folded into previous auto-commit  $MSG" >>"$LOG"
              FP="$(fingerprint)"; LAST_COMMIT_AT="$(now_epoch)"; FIRST_AT=""; CHANGED_AT="$LAST_COMMIT_AT"
              return 0
            fi
            git reset -q --soft "$PRE_FOLD"
            echo "$(date -Is) fold push rejected, fallback to a new commit" >>"$LOG"
          else
            git reset -q --soft "$PRE_FOLD"
            echo "$(date -Is) fold amend failed, fallback to a new commit" >>"$LOG"
          fi
        fi
        ;;
    esac
  fi
  git -c user.name="dsh cloud" -c user.email="dsh-cloud@users.noreply.github.com" \
    commit -q -m "$MSG" ${BODY:+-m "$BODY"} >>"$LOG" 2>&1 || return 1
  if git push -q origin "HEAD:$BRANCH" >>"$LOG" 2>&1; then
    echo "$(date -Is) pushed  $MSG" >>"$LOG"
    FP="$(fingerprint)"; LAST_COMMIT_AT="$(now_epoch)"; FIRST_AT=""; CHANGED_AT="$LAST_COMMIT_AT"
    return 0
  fi
  # 远端可能被别的电脑动过：rebase 一下再推
  echo "$(date -Is) push rejected, rebase and retry" >>"$LOG"
  if git pull --rebase -q origin "$BRANCH" >>"$LOG" 2>&1 && git push -q origin "HEAD:$BRANCH" >>"$LOG" 2>&1; then
    echo "$(date -Is) pushed after rebase  $MSG" >>"$LOG"
    FP="$(fingerprint)"; LAST_COMMIT_AT="$(now_epoch)"; FIRST_AT=""; CHANGED_AT="$LAST_COMMIT_AT"
    return 0
  fi
  git rebase --abort >>"$LOG" 2>&1 || true
  echo "$(date -Is) push FAILED  $MSG" >>"$LOG"
  return 1
}

tick() {
  [ -d "$WORKSPACE_DIR/.git" ] || return 0
  cur="$(fingerprint)"
  t="$(now_epoch)"
  if [ "$cur" != "$FP" ]; then
    FP="$cur"
    CHANGED_AT="$t"
    [ -n "$FIRST_AT" ] || FIRST_AT="$t"
  fi
  if ! dirty; then
    FIRST_AT=""
    save_state
    return 0
  fi
  if [ "$enabled" != "on" ]; then
    save_state
    return 0
  fi
  case "$mode" in
    manual)
      : ;;
    interval)
      [ -n "$LAST_COMMIT_AT" ] || LAST_COMMIT_AT="$t"
      [ $((t - LAST_COMMIT_AT)) -ge "$interval" ] && commit_now
      ;;
    *)
      [ -n "$CHANGED_AT" ] || CHANGED_AT="$t"
      [ -n "$FIRST_AT" ] || FIRST_AT="$t"
      if [ $((t - CHANGED_AT)) -ge "$idle_seconds" ] || [ $((t - FIRST_AT)) -ge "$max_wait" ]; then
        commit_now
      fi
      ;;
  esac
  save_state
}

show_status() {
  printf '模式：%s（enabled=%s）\n' "$mode" "$enabled"
  printf '参数：idle_seconds=%s  max_wait=%s  interval=%s  tick=%s  prefix=%s  squash_window_seconds=%s\n' \
    "$idle_seconds" "$max_wait" "$interval" "$tick" "$prefix" "$squash_window_seconds"
  if [ -d "$WORKSPACE_DIR/.git" ]; then
    printf '工作区：%s\n' "$WORKSPACE_DIR"
    if dirty; then
      printf '待提交：%s 个文件\n' "$(git -C "$WORKSPACE_DIR" status --porcelain | wc -l | tr -d ' ')"
      git -C "$WORKSPACE_DIR" status --short | head -10 | sed 's/^/  /'
    else
      printf '待提交：无（工作区是干净的）\n'
    fi
    printf '分支：%s  本地 HEAD：%s  远端：%s\n' "$BRANCH" \
      "$(git -C "$WORKSPACE_DIR" rev-parse --short HEAD 2>/dev/null)" \
      "$(git -C "$WORKSPACE_DIR" ls-remote origin "refs/heads/$BRANCH" 2>/dev/null | cut -c1-7)"
    printf '最近提交：\n'
    git -C "$WORKSPACE_DIR" log --oneline -5 2>/dev/null | sed 's/^/  /'
  else
    printf '工作区不存在：%s\n' "$WORKSPACE_DIR"
  fi
}

ACTION=daemon
ACTION_EXPLICIT=0
while [ $# -gt 0 ]; do
  case "$1" in
    --daemon)     ACTION=daemon; ACTION_EXPLICIT=1 ;;
    --status)     ACTION=status ;;
    --plan)       ACTION=plan ;;
    --now|--once) ACTION=now ;;
    --mode=*)     MODE_OVERRIDE="${1#--mode=}" ;;
    --idle=*)     IDLE_OVERRIDE="${1#--idle=}" ;;
    --interval=*) INT_OVERRIDE="${1#--interval=}" ;;
    --enable)     ENABLE_OVERRIDE=on ;;
    --disable)    ENABLE_OVERRIDE=off ;;
    --squash-window=*) SQUASH_OVERRIDE="${1#--squash-window=}" ;;
    --message=*)  MESSAGE_OVERRIDE="${1#--message=}" ;;
    --help|-h)    usage; exit 0 ;;
    *)            echo "未知参数：$1（--help 看用法）"; exit 2 ;;
  esac
  shift || true
done

load_conf
[ -n "$MODE_OVERRIDE" ] && mode="$MODE_OVERRIDE"
[ -n "$IDLE_OVERRIDE" ] && idle_seconds="$IDLE_OVERRIDE"
[ -n "$INT_OVERRIDE" ] && interval="$INT_OVERRIDE"
[ -n "$ENABLE_OVERRIDE" ] && enabled="$ENABLE_OVERRIDE"
[ -n "$SQUASH_OVERRIDE" ] && squash_window_seconds="$SQUASH_OVERRIDE"
if [ -n "$MODE_OVERRIDE$IDLE_OVERRIDE$INT_OVERRIDE$ENABLE_OVERRIDE$SQUASH_OVERRIDE" ]; then save_conf; fi
if [ -n "$MESSAGE_OVERRIDE" ]; then printf '%s\n' "$MESSAGE_OVERRIDE" > "$CLOUD_DIR/commit-msg"; fi

# 只改设置（--enable / --disable / --mode=… / --idle=… / --message=…）时改完就退出，不进守护循环
if [ "$ACTION" = daemon ] && [ "$ACTION_EXPLICIT" = 0 ] &&
   [ -n "$MODE_OVERRIDE$IDLE_OVERRIDE$INT_OVERRIDE$ENABLE_OVERRIDE$SQUASH_OVERRIDE${MESSAGE_OVERRIDE}" ]; then
  printf '已更新 %s\n  enabled=%s mode=%s idle_seconds=%s max_wait=%s interval=%s tick=%s prefix=%s squash_window_seconds=%s\n' \
    "$CONF" "$enabled" "$mode" "$idle_seconds" "$max_wait" "$interval" "$tick" "$prefix" "$squash_window_seconds"
  [ -n "$MESSAGE_OVERRIDE" ] && printf '下一次提交会用：%s\n' "$MESSAGE_OVERRIDE"
  exit 0
fi

case "$ACTION" in
  status) load_state; show_status; exit 0 ;;
  plan)   load_state; PLAN_ONLY=1; commit_now; exit $? ;;
  now)    load_state; PLAN_ONLY=0; commit_now || { echo "提交/推送失败，看 $LOG"; exit 1; }; save_state; exit 0 ;;
esac

PLAN_ONLY=0
load_state
echo "$(date -Is) daemon start mode=$mode idle=${idle_seconds}s max_wait=${max_wait}s enabled=$enabled" >>"$LOG"
while true; do
  tick
  sleep "${tick:-30}"
done
