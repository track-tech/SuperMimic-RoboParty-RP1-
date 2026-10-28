#!/usr/bin/env bash
# 评测 + 出视频
#   bash scripts/setup/06_eval_render.sh <UNI_SUPERMIMIC_ROOT> <REPO_ROOT> <ckpt.pt> [rp1|rpo|g1]
set -euo pipefail
USM="${1:?用法: 06_eval_render.sh <Uni-SuperMimic 根目录> <本仓库根目录> <ckpt.pt> [profile]}"
REPO_ROOT="${2:?缺本仓库根目录}"
CKPT="$(cd "$(dirname "$3")" && pwd)/$(basename "$3")"
PROFILE="${4:-rp1}"

case "$PROFILE" in
  g1)  unset SUPERMIMIC_ROBOT || true; SCENE="$USM/src/unisupermimic/assets/robots/g1/scene_supermimic.xml" ;;
  rp1) export SUPERMIMIC_ROBOT=rp1;    SCENE="$USM/src/unisupermimic/assets/robots/rp1/scene_supermimic.xml" ;;
  rpo) export SUPERMIMIC_ROBOT=rpo;    SCENE="$USM/src/unisupermimic/assets/robots/rpo/scene_supermimic.xml" ;;
  *)   echo "未知 profile: $PROFILE"; exit 1 ;;
esac
cd "$USM"
export HF_HUB_OFFLINE=1

echo "== 1) 全库评测（40 段，eval_mode）=="
python src/unisupermimic/tasks/motion_tracking/g1/supermimic/evaluate.py --ckpt "$CKPT" \
  | tail -30

echo
echo "== 2) 单段渲染（带参考幽灵）=="
OUT="${OUT_DIR:-$REPO_ROOT/_work}"
mkdir -p "$OUT"
SUPERMIMIC_CAM_DIST="${SUPERMIMIC_CAM_DIST:-2.6}" \
python src/unisupermimic/tasks/motion_tracking/g1/supermimic/render.py \
  --ckpt "$CKPT" --clip "${CLIP:-walk1_subject1}" --seconds "${SECONDS:-40}" \
  --fps 25 --width 1280 --height 720 --scene "$SCENE" \
  --output "$OUT/${PROFILE}_${CLIP:-walk1_subject1}.mp4"

echo
echo "== 3) 多段合集（可选）=="
echo "   python $REPO_ROOT/scripts/render/showcase_rp1.py --ckpt $CKPT \\"
echo "     --clips walk1_subject1,run1_subject2,dance2_subject1 --seconds 12,12,200 \\"
echo "     --scene $SCENE --out $OUT/${PROFILE}_showcase.mp4"
echo "   python $REPO_ROOT/scripts/render/stitch_showcase.py --out $OUT/${PROFILE}_showcase.mp4"
