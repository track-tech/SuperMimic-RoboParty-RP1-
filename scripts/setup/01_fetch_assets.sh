#!/usr/bin/env bash
# 下载 RoboParty 官方描述包，把网格放进 assets/robots/{rp1,rpo}/
#   bash scripts/setup/01_fetch_assets.sh [REPO_ROOT]
set -euo pipefail
REPO_ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "== 下载 rp1_description / rpo_description =="
curl -L --retry 3 -o "$TMP/rp1.tar.gz" \
  https://codeload.github.com/Roboparty/rp1_description/tar.gz/refs/heads/master
curl -L --retry 3 -o "$TMP/rpo.tar.gz" \
  https://codeload.github.com/Roboparty/rpo_description/tar.gz/refs/heads/main
mkdir -p "$TMP/rp1" "$TMP/rpo"
tar xzf "$TMP/rp1.tar.gz" -C "$TMP/rp1"
tar xzf "$TMP/rpo.tar.gz" -C "$TMP/rpo"

echo "== RP1 网格 -> assets/robots/rp1/meshes/ =="
# RP1 的 MJCF 用 <mesh file="meshes/x.STL"/> + meshdir="./"
mkdir -p "$REPO_ROOT/assets/robots/rp1/meshes"
cp -f "$TMP"/rp1/rp1_description-master/meshes/*.STL "$REPO_ROOT/assets/robots/rp1/meshes/"
echo "   $(ls "$REPO_ROOT/assets/robots/rp1/meshes" | wc -l) 个 STL（手部网格另行保留在描述包里）"

echo "== RPO 网格 -> assets/robots/rpo/ （平铺）=="
# RPO 的 MJCF 用 <mesh file="x.STL"/> + meshdir="./"
cp -f "$TMP"/rpo/rpo_description-main/meshes/*.STL "$REPO_ROOT/assets/robots/rpo/"
echo "   $(ls "$REPO_ROOT/assets/robots/rpo"/*.STL | wc -l) 个 STL"

echo "== 顺带留下原始 URDF/MJCF 供对照 =="
mkdir -p "$REPO_ROOT/assets/robots/rp1/_source" "$REPO_ROOT/assets/robots/rpo/_source"
cp -f "$TMP"/rp1/rp1_description-master/mjcf/*.xml "$REPO_ROOT/assets/robots/rp1/_source/" 2>/dev/null || true
cp -f "$TMP"/rpo/rpo_description-main/mjcf/*.xml "$REPO_ROOT/assets/robots/rpo/_source/" 2>/dev/null || true

echo "完成。"
