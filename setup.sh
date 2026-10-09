#!/usr/bin/env bash
# =============================================================================
#  DeepSeek Harness (dsh) on GitHub Codespaces —— 本机一键安装（macOS / Linux）
#
#  用法：
#      ./setup.sh --repo=你的用户名/仓库名        # 首次（或还没建 Codespace）
#      ./setup.sh                                 # 已经建好 Codespace 时
#      ./setup.sh --dry-run                       # 只检查，不改任何东西
# =============================================================================
set -u

KIT_VERSION="1.7.2"
CLOUD_SETUP_URL="https://raw.githubusercontent.com/Wz2-z/dsh-codespaces-kit/main/install/cloud-setup.sh"

REPO=""
CODESPACE=""
DRY_RUN=0
SKIP_LAUNCHER=0
usage() { sed -n '2,10p' "$0" 2>/dev/null || echo "用法：./setup.sh [--repo=owner/name] [--codespace=名字] [--dry-run] [--no-launcher]"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --repo)        shift || true; REPO="${1:-}" ;;
    --repo=*)      REPO="${1#--repo=}" ;;
    --codespace)   shift || true; CODESPACE="${1:-}" ;;
    --codespace=*) CODESPACE="${1#--codespace=}" ;;
    --dry-run|--check) DRY_RUN=1 ;;
    --no-launcher) SKIP_LAUNCHER=1 ;;
    -h|--help)     usage; exit 0 ;;
    *) echo "未知参数：$1（用 --help 看用法）"; exit 2 ;;
  esac
  shift || true
done

ok()   { printf '     \033[32m✓\033[0m %s\n' "$*"; }
info() { printf '       %s\n' "$*"; }
warn() { printf '     \033[33m!\033[0m %s\n' "$*"; }
step() { printf '\n[%s] \033[1m%s\033[0m\n' "$1" "$2"; }
die()  { printf '\n\033[31m✗ %s\033[0m\n' "$*"; exit 1; }

printf '\033[1mDeepSeek Harness · Codespaces 一键安装（本机 %s）\033[0m  v%s\n' "$(uname -s)" "$KIT_VERSION"
[ "$DRY_RUN" = 1 ] && printf '\033[33m模式：dry-run（只检查，不改任何东西）\033[0m\n'

# -----------------------------------------------------------------------------
step 1/8 '检查 GitHub CLI'
if command -v gh >/dev/null 2>&1; then
  ok "已经装好：$(gh --version | head -1)"
else
  cat <<'HINT'
     没找到 gh。先装它，再跑这个脚本：
       macOS：  brew install gh
       Debian/Ubuntu： sudo apt install gh     （或看 https://github.com/cli/cli#installation）
HINT
  die "缺少 GitHub CLI"
fi
if ! gh auth status >/dev/null 2>&1; then
  if [ "$DRY_RUN" = 1 ]; then
    warn "还没登录 gh（dry-run 不发起登录）"
  else
    info "需要一次浏览器授权：屏幕上的验证码 → https://github.com/login/device"
    gh auth login --hostname github.com --git-protocol https --web --scopes codespace,repo,read:org,workflow || die "gh auth login 没成功，再跑一次本脚本即可"
  fi
else
  ok "已经登录过 gh"
fi

# -----------------------------------------------------------------------------
step 2/8 '检查 Codespace'
CS="$CODESPACE"
if [ -z "$CS" ]; then
  LIST="$(gh codespace list --json name,state,repository 2>/dev/null || echo '[]')"
  if [ -n "$REPO" ]; then
    CS="$(printf '%s' "$LIST" | tr '{' '\n' | grep -F "\"$REPO\"" | sed -n 's/.*"name":"\([^"]*\)".*/\1/p' | head -1)"
  fi
  [ -z "$CS" ] && CS="$(printf '%s' "$LIST" | sed -n 's/.*"name":"\([^"]*\)".*/\1/p' | head -1)"
fi
if [ -n "$CS" ]; then
  ok "用这个 Codespace：$CS"
elif [ -n "$REPO" ]; then
  if [ "$DRY_RUN" = 1 ]; then
    warn "没有 Codespace，dry-run 不创建（会执行 gh codespace create -R $REPO）"
  else
    info "没有可用的 Codespace，按 $REPO 新建一个（2 核 / East US / 闲置 240 分钟）"
    CS="$(gh codespace create -R "$REPO" -m basicLinux32gb -l EastUs --idle-timeout 240m 2>&1 | tail -1)"
    [ -n "$CS" ] || die "创建 Codespace 失败（仓库名对不对？免费额度还在吗？）"
    ok "建好了：$CS"
  fi
else
  warn "没有可用的 Codespace：加 --repo=你的用户名/仓库名 再跑一次"
fi

# -----------------------------------------------------------------------------
step 3-7/8 '交给云端：Node → dsh → workspace → deploy key → 自动同步'
if [ -n "$CS" ]; then
  TMP="$(mktemp "${TMPDIR:-/tmp}/dsh-cloud-setup.XXXXXX")"
  if [ -f "$(dirname "$0")/cloud-setup.sh" ]; then
    cp "$(dirname "$0")/cloud-setup.sh" "$TMP"; info "用本地这份 cloud-setup.sh"
  elif [ "$DRY_RUN" = 1 ]; then
    warn "dry-run 且本地没有 cloud-setup.sh，跳过云端步骤"
  else
    curl -fsSL "$CLOUD_SETUP_URL" -o "$TMP" || die "下载 cloud-setup.sh 失败"
  fi
  if [ -f "$TMP" ]; then
    DRY_FLAG=""
    [ "$DRY_RUN" = 1 ] && DRY_FLAG=" --dry-run"
    if gh codespace cp -e -c "$CS" "$TMP" 'remote:/tmp/dsh-cloud-setup.sh' 2>/dev/null; then
      gh codespace ssh -c "$CS" -- "bash /tmp/dsh-cloud-setup.sh$DRY_FLAG" ||
        warn "云端脚本返回非 0：把上面的输出贴给 AI 继续修"
    elif [ "$DRY_RUN" = 1 ]; then
      warn "上传脚本失败（dry-run 不重试）"
    else
      warn "上传脚本失败，改成让容器自己下载"
      gh codespace ssh -c "$CS" -- "curl -fsSL $CLOUD_SETUP_URL -o /tmp/dsh-cloud-setup.sh && bash /tmp/dsh-cloud-setup.sh" ||
        warn "云端脚本返回非 0：把上面的输出贴给 AI 继续修"
    fi
  fi
  rm -f "$TMP"
else
  warn "没有 Codespace，跳过云端步骤"
fi

# -----------------------------------------------------------------------------
step 8/8 '本机验证 + 桌面启动器'
if [ "$SKIP_LAUNCHER" = 0 ]; then
  LAUNCH_DIR="$HOME/.local/share/dsh-cloud"
  mkdir -p "$LAUNCH_DIR" 2>/dev/null || true
  for pair in "start:start.sh:启动 dsh" "update:update.sh:更新 dsh"; do
    name="${pair%%:*}"; rest="${pair#*:}"; cloud_script="${rest%%:*}"; title="${rest#*:}"
    launcher="$LAUNCH_DIR/$name-dsh.sh"
    if [ "$DRY_RUN" = 1 ]; then
      info "(dry-run) 会写 $launcher"
    else
      cat > "$launcher" <<LAUNCH
#!/usr/bin/env bash
set -u
CS="$CS"
CLOUD="/workspaces/$REPO/.dsh-cloud"
LOG="\$HOME/.cache/dsh-cloud-$name.log"
mkdir -p "\$(dirname "\$LOG")"
echo "$title"
gh codespace ssh -c "\$CS" -- "bash \$CLOUD/$cloud_script" | tee "\$LOG"
URL="\$(grep -a -o 'http://127.0.0.1:3080[^ ]*' "\$LOG" | tail -1)"
( gh codespace ports forward 3080:3080 -c "\$CS" >/dev/null 2>&1 & )
sleep 3
if [ -n "\${URL:-}" ]; then
  (xdg-open "\$URL" >/dev/null 2>&1 || open "\$URL" >/dev/null 2>&1 || echo "打开这个地址：\$URL") &
else
  echo "没读到地址，看 \$LOG"
fi
LAUNCH
      chmod +x "$launcher"
    fi
    DESKTOP="$HOME/Desktop"
    [ -d "$DESKTOP" ] || DESKTOP="$HOME/桌面"
    if [ -d "$DESKTOP" ] && [ "$DRY_RUN" = 0 ]; then
      ln -sf "$launcher" "$DESKTOP/$name-dsh.command"
    fi
  done
  [ "$DRY_RUN" = 0 ] && ok "启动器：$LAUNCH_DIR（桌面也有快捷方式）"
else
  info "按 --no-launcher 跳过"
fi

if [ -n "$CS" ] && [ "$DRY_RUN" = 0 ]; then
  info '建隧道并试着访问 127.0.0.1:3080'
  ( gh codespace ports forward 3080:3080 -c "$CS" >/dev/null 2>&1 & )
  sleep 6
  CODE="$(curl -s -o /dev/null -w '%{http_code}' -m 8 http://127.0.0.1:3080/ || echo 000)"
  case "$CODE" in
    401) ok '隧道通了：3080 返回 401（说明需要 token，正常）' ;;
    200) ok '隧道通了：3080 返回 200' ;;
    *)   warn "隧道暂时没通（返回 $CODE）：稍后双击桌面启动器再看，或让 AI 排查" ;;
  esac
fi

printf '\n\033[42;30m ✅ Installation complete \033[0m\n\n'
printf 'dsh-codespaces-kit v%s\n' "$KIT_VERSION"
printf '以后启动：双击桌面的启动器（使用期间别关 ports forward 那个进程）\n'
printf '升级 dsh：桌面上的「更新 dsh」\n'
printf '看额度：https://github.com/settings/billing  ·  省额度：https://github.com/codespaces 点 Stop\n\n'
