# 本地存档说明（算力机到期前的备份）

云端算力机（`ssh -p 31744 root@183.147.142.40`）随时会到期，这里记录**本地保存了什么、
没保存什么、以及怎么在没有那台机器的情况下继续**。

存档位置：`supermimic/_server_archive/`

---

## 一、已经在本地的（不依赖那台机器）

| 内容 | 位置 | 说明 |
|---|---|---|
| 全部代码补丁 | `_repo/`（已推到 GitHub `main`） | 71 个文件：三个 profile、task 配置、MJCF、GMR 补丁、脚本 |
| 交接文档 | `RP1-迁移进度与交接.md` | 含本次会话总结、所有坑、Mars 的结论 |
| 演示视频 / 图 | 本目录 `*.mp4` / `*.png` | 11 分钟主演示、走跑对比、Mars 走跑 |
| 工具脚本 | 本目录 `*.py` | `remote_exec.py`、`retime.py`、`reground.py`、`render_mars.py`、各种 sweep/diag |

## 二、从服务器拉回来的（`_server_archive/`，共约 370 MB）

| 文件 | 大小 | 内容 |
|---|---|---|
| `mars_archive_full.tgz` | 425 MB | **全量包**（所有 ckpt + 动作数据 + 日志 + 脚本），23:50 链路恢复后补拉的 |
| `mars_essentials.tgz` | 191 MB | 关键子集（见下方 `_ess/`） |
| `rp1_motions_v3.tgz` | 97 MB | RP1 那 40 段重定向 CSV（产出 0.714/0.750 的原始输入） |
| `mars_assets_motions.tgz` | 6 MB | Mars 的 40 段（重定时 + 逐帧落根后） |

`_ess/` 展开：
```
_ess/
├── ckpt/
│   ├── rp1_30k_ckpt026000.pt     ← **最终最好：norm_return 0.758 / 3-40**
│   ├── rp1_30k_ckpt030000.pt     ← 0.731 / 5-40
│   ├── rp1_20k_ckpt020000.pt     ← 0.750 / **2-40**（失败最少，只剩两段舞蹈）
│   ├── rp1_4096_ckpt012000.pt    ← 0.714 / 3-40
│   ├── rp1_20k_ckpt008000.pt
│   ├── g1_ckpt006000.pt          ← G1 基线 0.774 / 5-40
│   └── …
├── rp1_30k_last.pt ← 207 MB，30000 轮的完整状态，**可以 resume 续训**
├── rp1_20k_last.pt ← 207 MB，20000 轮的完整状态
├── runs/          27 个 run 的 train_log.csv / args.json / run_config.json（训练曲线全在）
├── ik_configs/    bvh_lafan1_to_{rp1,rpo,mars_v3}.json（含调好的 scale 0.82 / foot dz −0.07）
├── configs/       mars_super_mimic 三个 yaml + Mars 的 MJCF 与场景
├── scripts/       服务器上 157 个 .sh/.py（含所有 _xxx.sh 实验脚本、mars_patch/）
└── eval_logs/     每次 40 段评测的完整输出
```

完整性校验：`bvh_lafan1_to_rp1.json` 的 SHA256 本地与服务器一致（`5A6C3125…`），ckpt 大小
71,322,053 / 71,781,957 字节与服务器相同。

**用这些能做什么**：直接跑推理/评测/渲染（`evaluate.py --ckpt ...`、`render.py`），
或者在新机器上接着训——但**不能 resume**，因为 resume 需要 `last.pt`（含优化器状态，207 MB）。

## 三、故意没拉的（都能重新生成）

| 内容 | 重新生成方式 | 代价 |
|---|---|---|
| LAFAN1 BVH 40 段（178 MB） | `scripts/setup/04_fetch_motions.sh`（hf-mirror） | ~3 分钟 |
| 机器人网格 STL（RP1/RPO/Mars） | `scripts/setup/01_fetch_assets.sh` + Mars 的 tar | ~1 分钟 |
| 重定向后的动作 CSV（341 MB） | 重定向 40 段 ≈ 4 分钟/机器人 | ~10 分钟 |
| `last.pt`（恢复训练用） | 训练时自动生成 | 需重训 |
| 其余 checkpoint（每个 68 MB） | 重训 | 每 2000 轮一个 |

## 四、换到新机器的最小路径

```bash
# 1) 拿到代码
git clone https://github.com/track-tech/SuperMimic-RoboParty-RP1-.git
git clone https://github.com/Motphys/Uni-SuperMimic.git ~/Uni-SuperMimic
git clone https://github.com/Roboparty/GMR.git ~/GMR

# 2) 依赖（两套 venv，见 README）
#    usm-env: py3.11 + torch 2.9 + triton 3.4.0 + unilab 1.5.2 + mujoco（mjwarp）
#    gmr-env: py3.12 + mujoco 3.17 + mink 1.3.0 + scipy + daqp + imageio

# 3) 打补丁 + 拿资产 + 重定向
bash repo/scripts/setup/01_fetch_assets.sh repo
bash repo/scripts/setup/02_apply_patches.sh ~/Uni-SuperMimic repo
bash repo/scripts/setup/03_setup_gmr.sh ~/GMR repo
bash repo/scripts/setup/04_fetch_motions.sh ~/GMR ~/Uni-SuperMimic repo

# 4) 用存档里的 IK 配置覆盖（这一步很关键，scale/offset 是调过的）
cp _ess/ik_configs/*.json ~/GMR/general_motion_retargeting/ik_configs/

# 5) 评测 / 渲染（不需要重训）
SUPERMIMIC_ROBOT=rp1 python src/unisupermimic/tasks/motion_tracking/g1/supermimic/evaluate.py \
  --ckpt _ess/ckpt/rp1_4096_ckpt012000.pt
```

## 五、还欠的

- **20000 轮那轮的最终 ckpt**（期望 ~23:25 训完）：到点后评 16000/20000，把最好的那个再拉一次
- 如果那台机器提前挂了：现有最好的就是 `rp1_4096_ckpt012000.pt`（0.714 / 3-40），
  以及 `rp1_20k_ckpt008000.pt`（训练曲线同位置 sim_rew 0.715，评测未做）

## 六、安全提醒

服务器 root 密码在本对话里出现过，机器到期后如果还要复用这个密码，记得换。
