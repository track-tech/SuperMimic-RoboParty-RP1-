#!/usr/bin/env bash
# 训练
#   bash scripts/setup/05_train.sh <UNI_SUPERMIMIC_ROOT> [rp1|rpo|g1] [额外 hydra 覆盖...]
set -euo pipefail
USM="${1:?用法: 05_train.sh <Uni-SuperMimic 根目录> [profile] [覆盖...]}"
PROFILE="${2:-rp1}"
shift || true
shift || true

case "$PROFILE" in
  g1)  unset SUPERMIMIC_ROBOT || true ;;
  rp1) export SUPERMIMIC_ROBOT=rp1 ;;
  rpo) export SUPERMIMIC_ROBOT=rpo ;;
  *)   echo "未知 profile: $PROFILE"; exit 1 ;;
esac

cd "$USM"
export HF_HUB_OFFLINE=1          # 服务器/离线环境必须；G1 网格要预置到 unilab assets
echo "profile=$PROFILE  task=${PROFILE}_super_mimic/mjwarp"
python -m unisupermimic.scripts.train_supermimic \
  task="${PROFILE}_super_mimic/mjwarp" \
  algo.num_envs="${NUM_ENVS:-2048}" \
  algo.iterations="${ITERS:-12000}" \
  "$@"
