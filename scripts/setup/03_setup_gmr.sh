#!/usr/bin/env bash
# 给 RoboParty GMR 打补丁：注册 rp1、headless 化、挂上 RK1 的机器人资产
#   bash scripts/setup/03_setup_gmr.sh <GMR_ROOT> [REPO_ROOT]
set -euo pipefail
GMR="${1:?用法: 03_setup_gmr.sh <GMR 根目录> [本仓库根目录]}"
REPO_ROOT="${2:-$(cd "$(dirname "$0")/../.." && pwd)}"

[ -d "$GMR/general_motion_retargeting" ] || {
  echo "!! $GMR 看起来不是 GMR 的根目录" >&2
  exit 1
}

echo "== 备份并覆盖 GMR 补丁文件 =="
mkdir -p "$GMR/_gmr_backup"
while IFS= read -r f; do
  rel="${f#"$REPO_ROOT/gmr_patches/"}"
  if [ -f "$GMR/$rel" ]; then
    mkdir -p "$GMR/_gmr_backup/$(dirname "$rel")"
    cp -n "$GMR/$rel" "$GMR/_gmr_backup/$rel"
  fi
done < <(find "$REPO_ROOT/gmr_patches" -name '*.py' -o -name '*.json')
cp -rv "$REPO_ROOT/gmr_patches/." "$GMR/" | sed 's/^/   /'

echo "== 把机器人资产挂到 GMR/assets（IK 需要模型和网格）=="
USM_SRC="${UNI_SUPERMIMIC_ROOT:-}"
for robot in rp1 rpo; do
  if [ -n "$USM_SRC" ] && [ -d "$USM_SRC/src/unisupermimic/assets/robots/$robot" ]; then
    src="$USM_SRC/src/unisupermimic/assets/robots/$robot"
  else
    src="$REPO_ROOT/assets/robots/$robot"
  fi
  [ -d "$src" ] || { echo "   skip $robot（找不到资产）"; continue; }
  dst="$GMR/assets/$robot"
  rm -rf "$dst"
  mkdir -p "$dst"
  cp -r "$src/." "$dst/"
  echo "   $robot -> $dst"
done

echo "== 校验：能加载 rp1 模型 =="
GMR_ROOT="$GMR" python - <<'PY' || echo "   加载失败，检查 assets/rp1/meshes 是否到位"
import sys, mujoco
sys.path.insert(0, __import__("os").environ["GMR_ROOT"])
from general_motion_retargeting.params import ROBOT_XML_DICT
m = mujoco.MjModel.from_xml_path(str(ROBOT_XML_DICT["rp1"]))
print(f"   rp1 ok: nq={m.nq} nv={m.nv} nu={m.nu}")
PY

echo "完成。重定向时用 --robot rp1（或 rpo）。"
