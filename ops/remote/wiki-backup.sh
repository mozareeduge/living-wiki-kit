#!/usr/bin/env bash
# Backup half 1: push the instance repo to a private git remote.
# Backup half 2: snapshot the encrypted EBS data volume (needs the aws CLI and an instance role
# that may call ec2:CreateSnapshot only). Either half is skipped, with a message, when unset.
set -euo pipefail
cd "${WIKI_ROOT:-$(dirname "$0")/../..}"

if [ -n "${BACKUP_GIT_REMOTE:-}" ]; then
  git remote get-url backup >/dev/null 2>&1 || git remote add backup "$BACKUP_GIT_REMOTE"
  git push backup "HEAD:${BACKUP_GIT_BRANCH:-main}"   # plain push: never --force
  echo "backup: git push ok"
else
  echo "backup: SKIP git push (BACKUP_GIT_REMOTE not set)"
fi

if [ -n "${BACKUP_EBS_VOLUME_ID:-}" ]; then
  aws ec2 create-snapshot --volume-id "$BACKUP_EBS_VOLUME_ID" \
    --description "living-wiki backup $(date -u +%Y-%m-%dT%H:%MZ)" >/dev/null
  echo "backup: EBS snapshot requested"
else
  echo "backup: SKIP EBS snapshot (BACKUP_EBS_VOLUME_ID not set)"
fi
