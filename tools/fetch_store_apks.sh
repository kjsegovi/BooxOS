#!/bin/bash
# Fetch the bundled APKs (app stores from f-droid.org, Readest from GitHub) and check them against the
# pinned SHA-256 (cross-checked 2026-11-18 against F-Droid's index-v2: file hash
# and signer certificate). Output: device/onyx/GoColor7_2/prebuilt/apps/*.apk
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=device/onyx/GoColor7_2/prebuilt/apps
fetch() {  # url dest sha256
  local tmp; tmp=$(mktemp)
  curl -fsSL -o "$tmp" "$1"
  echo "$3  $tmp" | shasum -a 256 -c - >/dev/null || { echo "hash mismatch: $1" >&2; rm -f "$tmp"; exit 1; }
  mv "$tmp" "$OUT/$2"; echo "ok $2"
}
# Aurora Store 4.8.4 (76); signer 5c83c7672b929955dc0a1db89a5e6ae4389e2eae7ec939956041694e5815f532
fetch https://f-droid.org/repo/com.aurora.store_76.apk com.aurora.store.apk \
  fd9c75d90d0f4a7c132b9b4a5a2cf1992a45e03b8d8ff988b7dcfbc0db2c4d11
# F-Droid 2.0.3 (2000053); signer 43238d512c1e5eb2d6569f4a3afbf5523418b82e0a3ed1552770abb9a9c9ccab
fetch https://f-droid.org/repo/org.fdroid.fdroid_2000053.apk org.fdroid.fdroid.apk \
  dac55a0d17b1edf7e7286b48cfbd70c7c52fbb32a00af062c68830a437c47959
# Readest 0.12.20 GitHub build (developer key, works without Google Play); digest
# matches GitHub's release asset; signer 652d1167761229141842cb3d1850b6e47e46e12f4be47f5a6c14b6d712741e82
fetch https://github.com/readest/readest/releases/download/v0.12.20/Readest_0.12.20_arm64.apk com.bilingify.readest.apk \
  0f8278610ba9fc5e9852b5f5a382a6f928e0c1607e957d8c34a8447f1be6ed1a
