#!/bin/bash
# Encrypt/decrypt Involvex browser backup files for Syncthing transfer.
# Uses AES-256-CBC + PBKDF2 via OpenSSL (available in WSL2 and Termux).
set -euo pipefail

usage() {
  echo "Usage: INVOLVEX_BACKUP_KEY=passphrase $0 encrypt|decrypt <input> <output>"
  exit 1
}

[[ $# -eq 3 ]] || usage
ACTION="$1"
INPUT="$2"
OUTPUT="$3"
KEY="${INVOLVEX_BACKUP_KEY:-}"

if [[ -z "${KEY}" ]]; then
  read -rsp "Backup passphrase: " KEY
  echo
fi

case "${ACTION}" in
  encrypt)
    openssl enc -aes-256-cbc -pbkdf2 -salt -in "${INPUT}" -out "${OUTPUT}" -pass "pass:${KEY}"
    echo "Encrypted: ${OUTPUT}"
    ;;
  decrypt)
    openssl enc -d -aes-256-cbc -pbkdf2 -in "${INPUT}" -out "${OUTPUT}" -pass "pass:${KEY}"
    echo "Decrypted: ${OUTPUT}"
    ;;
  *)
    usage
    ;;
esac
