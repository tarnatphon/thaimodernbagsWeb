#!/usr/bin/env bash
# Manually deploy only the public website files to cPanel over SFTP.
# The script never reads or stores hosting passwords/keys.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HOST_ALIAS="${SFTP_HOST_ALIAS:-tmb-web}"
FILES=("index.html" "styles.css" "script.js" "public/images/hero-bags.jpg")
STAMP="$(date '+%Y%m%d-%H%M%S')"
BACKUP_DIR="$HOME/Library/Application Support/ThaiModernBags/deploy-backups/$STAMP"

if ! command -v sftp >/dev/null 2>&1; then
  echo "Error: OpenSSH sftp is not available. On macOS it is normally included with the system." >&2
  exit 1
fi

for file in "${FILES[@]}"; do
  if [[ ! -f "$ROOT_DIR/$file" ]]; then
    echo "Error: required website file is missing: $file" >&2
    exit 1
  fi
done

printf 'SFTP host alias [%s]: ' "$HOST_ALIAS"
read -r entered_alias
if [[ -n "$entered_alias" ]]; then HOST_ALIAS="$entered_alias"; fi
if [[ ! "$HOST_ALIAS" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Error: use a simple SSH config host alias (letters, numbers, dot, underscore, hyphen)." >&2
  exit 1
fi

printf 'Remote website folder (for example public_html): '
read -r REMOTE_ROOT
REMOTE_ROOT="${REMOTE_ROOT%/}"
if [[ -z "$REMOTE_ROOT" || ! "$REMOTE_ROOT" =~ ^[A-Za-z0-9_./-]+$ ]]; then
  echo "Error: enter a remote path using only letters, numbers, slash, dot, underscore, or hyphen." >&2
  exit 1
fi
case "/$REMOTE_ROOT/" in
  *"/../"*) echo "Error: parent-directory paths (..) are not allowed." >&2; exit 1 ;;
esac

cat <<EOF

This will upload ONLY these public files to $HOST_ALIAS:$REMOTE_ROOT
  index.html
  styles.css
  script.js
  public/images/hero-bags.jpg

The previous versions will be downloaded to:
  $BACKUP_DIR
The local AI helper and tools/ folder will NOT be uploaded.
EOF
printf 'Type DEPLOY to continue: '
read -r confirm
if [[ "$confirm" != "DEPLOY" ]]; then
  echo "Cancelled. Nothing was uploaded."
  exit 0
fi

mkdir -p "$BACKUP_DIR"

# The batch backs up existing remote copies locally first. Missing remote files
# are expected on the initial deployment, so those get commands are non-fatal.
# Only the public file allowlist above is downloaded or uploaded.
sftp -b - "$HOST_ALIAS" <<SFTP_BATCH
cd "$REMOTE_ROOT"
lcd "$BACKUP_DIR"
-get -p "index.html" "index.html"
-get -p "styles.css" "styles.css"
-get -p "script.js" "script.js"
-get -p "public/images/hero-bags.jpg" "hero-bags.jpg"
-mkdir "public"
-mkdir "public/images"
put "$ROOT_DIR/index.html" "index.html"
put "$ROOT_DIR/styles.css" "styles.css"
put "$ROOT_DIR/script.js" "script.js"
put "$ROOT_DIR/public/images/hero-bags.jpg" "public/images/hero-bags.jpg"
SFTP_BATCH

echo
echo "Deployment complete. Review the public site in your browser."
echo "Local pre-deploy backup: $BACKUP_DIR"
