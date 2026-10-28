#!/usr/bin/env bash
# 把 patches/ 覆盖到 Uni-SuperMimic 的 checkout 上，并放入机器人资产
#   bash scripts/setup/02_apply_patches.sh <UNI_SUPERMIMIC_ROOT> [REPO_ROOT]
set -euo pipefail
USM="${1:?用法: 02_apply_patches.sh <Uni-SuperMimic 根目录> [本仓库根目录]}"
REPO_ROOT="${2:-$(cd "$(dirname "$0")/../.." && pwd)}"

[ -d "$USM/src/unisupermimic" ] || {
  echo "!! $USM 看起来不是 Uni-SuperMimic 的根目录（缺 src/unisupermimic）" >&2
  exit 1
}

echo "== 备份将被覆盖的上游文件 -> _usm_backup/ =="
mkdir -p "$USM/_usm_backup"
while IFS= read -r f; do
  rel="${f#"$REPO_ROOT"/patches/unisupermimic/}"
  if [ -f "$USM/$rel" ]; then
    mkdir -p "$USM/_usm_backup/$(dirname "$rel")"
    cp -n "$USM/$rel" "$USM/_usm_backup/$rel"
  fi
done < <(find "$REPO_ROOT/patches/unisupermimic" -name '*.py' -o -name '*.yaml')

echo "== 覆盖 patched 文件 =="
cp -rv "$REPO_ROOT/patches/unisupermimic/src" "$USM/" | sed 's/^/   /'

echo "== 放入机器人资产（MJCF + 网格 + scene）=="
for robot in rp1 rpo; do
  src="$REPO_ROOT/assets/robots/$robot"
  dst="$USM/src/unisupermimic/assets/robots/$robot"
  [ -d "$src" ] || { echo "   skip $robot（缺 $src，先跑 01_fetch_assets.sh）"; continue; }
  mkdir -p "$dst"
  cp -r "$src/." "$dst/"
  echo "   $robot -> $dst"
done

echo "== 校验：三个 profile 的维度 =="
cd "$USM"
for p in g1 rpo rp1; do
  SUPERMIMIC_ROBOT=$p python - <<'PY' 2>/dev/null || echo "   $p 导入失败（检查依赖）"
from unisupermimic.tasks.motion_tracking.g1.supermimic import mdp, robot
print(f"   profile={robot.ROBOT_PROFILE:4s} joints={mdp.NUM_J:2d} obs={mdp.OBS_DIM:3d} "
      f"xi={mdp.XI_DIM:2d} goal={mdp.GOAL_FRAME_DIM:2d}")
PY
done

echo "完成。注意：运行训练/评测/渲染时必须设置匹配的 SUPERMIMIC_ROBOT。"
