#!/usr/bin/env bash
# 下载 LAFAN1 BVH 并重定向到 RP1（40 段，10 进程并行约 6 分钟）
#   bash scripts/setup/04_fetch_motions.sh <GMR_ROOT> <UNI_SUPERMIMIC_ROOT> [REPO_ROOT]
set -euo pipefail
GMR="${1:?用法: 04_fetch_motions.sh <GMR 根目录> <Uni-SuperMimic 根目录> [本仓库根目录]}"
USM="${2:?缺 Uni-SuperMimic 根目录}"
REPO_ROOT="${3:-$(cd "$(dirname "$0")/../.." && pwd)}"

WORK="${WORK_DIR:-$REPO_ROOT/_work}"
BVH_DIR="${BVH_DIR:-$WORK/lafan1_bvh}"
OUT_DIR="${OUT_DIR:-$USM/src/unisupermimic/assets/motions/rp1/lafan1_supermimic}"
PROCS="${PROCS:-10}"
HF_MIRROR="${HF_MIRROR:-https://hf-mirror.com/datasets/johnny095212/lafan1/resolve/main}"

mkdir -p "$BVH_DIR" "$OUT_DIR"

# Uni-SuperMimic 的 G1 动作库就是这 40 段，保证三台机器人用同一套
CLIPS="dance1_subject1 dance1_subject2 dance1_subject3 dance2_subject1 dance2_subject2
dance2_subject3 dance2_subject4 dance2_subject5 fallAndGetUp1_subject1 fallAndGetUp1_subject4
fallAndGetUp1_subject5 fallAndGetUp2_subject2 fallAndGetUp2_subject3 fallAndGetUp3_subject1
fight1_subject2 fight1_subject3 fight1_subject5 fightAndSports1_subject1 fightAndSports1_subject4
jumps1_subject1 jumps1_subject2 jumps1_subject5 run1_subject2 run1_subject5 run2_subject1
run2_subject4 sprint1_subject2 sprint1_subject4 walk1_subject1 walk1_subject2 walk1_subject5
walk2_subject1 walk2_subject3 walk2_subject4 walk3_subject1 walk3_subject2 walk3_subject3
walk3_subject4 walk3_subject5 walk4_subject1"

echo "== 下载 LAFAN1 BVH（HF 镜像，40 段约 186 MB）=="
for c in $CLIPS; do
  dst="$BVH_DIR/$c.bvh"
  [ -s "$dst" ] && continue
  curl -sSL --retry 3 -o "$dst.part" "$HF_MIRROR/$c.bvh" && mv "$dst.part" "$dst" \
    || echo "   ! $c 下载失败（稍后重试即可）"
done
echo "   $(ls "$BVH_DIR"/*.bvh 2>/dev/null | wc -l) 段 BVH"

echo "== 重定向到 RP1（28 DoF）=="
cd "$REPO_ROOT"
ls "$BVH_DIR"/*.bvh | sed 's|.*/||; s|\.bvh$||' | sort \
  | xargs -P "$PROCS" -I{} python scripts/retarget/retarget_rp1.py \
      --bvh_dir "$BVH_DIR" --out_dir "$OUT_DIR" --robot rp1 --only {} \
  || true

echo "== 结果 =="
echo "   CSV: $(ls "$OUT_DIR"/*.csv 2>/dev/null | wc -l) 段；每段 7 + 28 = 35 列，30 fps"
echo "   把 OUT_DIR 下的 CSV 路径写进 conf/.../task/rp1_super_mimic/base.yaml 的 motion_files"
