# SuperMimic on RoboParty RP1 (28 DoF)

把 [Uni-SuperMimic](https://github.com/Motphys/Uni-SuperMimic)（SuperMimic 在 UniLab 上的独立复现）
移植到 **RoboParty RP1**（28 个驱动关节），并让同一份代码同时支持 **Unitree G1**（29 DoF）
和 **RoboParty RPO / Origin**（23 DoF）。

> **English TL;DR.** A patch set + asset pipeline + retargeting config that runs the
> SuperMimic world-model RL algorithm on RoboParty's RP1 humanoid. Three robots are
> supported through one `SUPERMIMIC_ROBOT={g1|rp1|rpo}` switch. Deterministic 40-clip
> evaluation: G1 0.774 / 5 failed, **RP1 0.647 / 8 failed**, RPO 0.557 / 11 failed.

---

## 结果（同一套 40 段 LAFAN1 动作、eval_mode）

| 机器人 | DoF | 最佳 ckpt | norm_return | 失败段数 | 非摔倒类成功率 |
|---|---|---|---|---|---|
| Unitree G1 | 29 | 6000 | 0.774 | 5/40 | 35/36 = 97% |
| **RoboParty RP1** | **28** | **10000** | **0.647** | **8/40** | **34/37 = 92%** |
| RoboParty RPO | 23 | 12000 | 0.557 | 11/40 | 28/32 = 88% |

- 训练规模：2048 envs × 12000 轮，单张 RTX 4090 约 2 小时 10 分。
- RP1 的 8 段失败里 3 段是 `fallAndGetUp*`（"摔倒再爬起来"，G1 也失败）。
- RP1 各 checkpoint：6000 → 0.551/13 段；**10000 → 0.647/8 段**；12000 → 0.630/11 段。

曲线与失败清单见 [RESULTS.md](RESULTS.md)，完整交接记录（含踩过的坑）见
[docs/RP1-迁移进度与交接.md](docs/RP1-迁移进度与交接.md)。

---

## 仓库内容

```
patches/unisupermimic/   # 对 Uni-SuperMimic 的改动，保持上游相对路径
  src/unisupermimic/tasks/motion_tracking/g1/supermimic/*.py
  src/unisupermimic/conf/supermimic/task/{rp1,rpo}_super_mimic/*.yaml
assets/robots/rp1/       # RP1 的 MuJoCo 模型（执行器/solver 已适配）
assets/robots/rpo/       # RPO 的 MuJoCo 模型
gmr_patches/             # 对 RoboParty GMR 的改动（IK 配置 + 注册 + headless）
scripts/
  setup/                 # 一键复现脚本
  retarget/              # 自己写的 headless 重定向（原版依赖 MuJoCo 窗口）
  assets/                # MJCF → position 执行器 / 加 stand keyframe / 补 geom 名
  checks/                # 站立、增益、参考动作质量等诊断脚本
  render/                # 出视频 + 拼图 + 左右并排
  analysis/              # 训练曲线对比
docs/                    # 交接文档与图
```

**不包含**（体积或授权原因，用 `scripts/setup/` 里的脚本重新生成）：
网格 STL、40 段重定向 CSV、checkpoint、演示 mp4。

---

## 快速开始

```bash
# 0) 依赖：Python 3.11 + torch + triton 3.4.0 + unilab 1.5.2 + mujoco；重定向另开一个 3.12 venv
git clone https://github.com/Motphys/Uni-SuperMimic.git ~/Uni-SuperMimic
git clone https://github.com/Roboparty/GMR.git          ~/GMR
git clone <this repo>                                   ~/sm-rp1

# 1) 拉机器人网格（RoboParty 官方描述包，CERN-OHL-W-2.0）
bash scripts/setup/01_fetch_assets.sh ~/sm-rp1

# 2) 应用补丁（幂等，改了哪些文件见 patches/）
bash scripts/setup/02_apply_patches.sh ~/Uni-SuperMimic ~/sm-rp1

# 3) 装 GMR 补丁（IK 配置 + headless 化）
bash scripts/setup/03_setup_gmr.sh ~/GMR ~/sm-rp1

# 4) 下载 LAFAN1 BVH 并重定向到 RP1（40 段，10 进程并行约 6 分钟）
bash scripts/setup/04_fetch_motions.sh ~/sm-rp1 ~/GMR ~/Uni-SuperMimic

# 5) 训练（约 2 小时 10 分）
bash scripts/setup/05_train.sh ~/Uni-SuperMimic rp1

# 6) 评测 + 出视频
bash scripts/setup/06_eval_render.sh ~/Uni-SuperMimic ~/sm-rp1 <ckpt.pt>
```

---

## 三个 profile 怎么切

一份代码、三个机器人，靠环境变量选择：

```bash
SUPERMIMIC_ROBOT=g1   uilab ... task=g1_super_mimic/mjwarp    # 默认，29 DoF
SUPERMIMIC_ROBOT=rp1  uilab ... task=rp1_super_mimic/mjwarp   # RP1，28 DoF
SUPERMIMIC_ROBOT=rpo  uilab ... task=rpo_super_mimic/mjwarp   # RPO，23 DoF
```

`robot.py` 末尾的开关按环境变量动态 import `robot_rp1.py` / `robot_rpo.py`，三个模块导出的
变量名一致（沿用上游的 `G1_JOINT_NAMES` 名字），因此 `kinematics.py` / `manager_terms.py`
的调用点一行都不用改。**环境变量必须和模型匹配**，否则关节表和观测维度对不上。

维度是从关节数和跟踪刚体数推出来的，不再写死：

| | G1 | RP1 | RPO |
|---|---|---|---|
| 关节数 | 29 | 28 | 23 |
| 跟踪刚体 | 14 | 14 | 14 |
| obs | 99 | 96 | 81 |
| context (ξ) | 33 | 32 | 27 |
| goal/frame | 73 | 71 | 61 |
| critic 额外 | 113 | 111 | 101 |

---

## 对上游 Uni-SuperMimic 改了什么

| 文件 | 改动 | 为什么 |
|---|---|---|
| `robot.py` | 末尾加 profile 开关（g1/rpo/rp1） | 上游把 G1 写死 |
| `robot_rp1.py` / `robot_rpo.py` | 新增 | 关节表、跟踪刚体、碰撞 geom、力矩表、站姿、`TORSO_BODY_NAME` |
| `mdp.py` | `NUM_J / OBS_DIM / XI_DIM / GOAL_FRAME_DIM / CRITIC_EXTRA` 全部改为推导 | 支持任意 DoF |
| `motion.py` | CSV 列数 `36` → `7 + NUM_J` | 同上 |
| `manager_terms.py` | 6 处 `context[:, 1:30]` / `xi[:, 30:33]` 改成 `1+NUM_J` 形式；`tensor_body_names` 与 `find_bodies("torso_link")` 改用 profile 常量 | 同上 |
| `env.py` | `geom_names is None` 时不覆盖 | RPO 的 MJCF 没有具名 geom |
| `registry.py` | 注册 `RP1SuperMimic` / `RPOSuperMimic` | 任务名要和 config 目录对应 |
| `evaluate.py` | `make_eval_env` 按 run 目录名推断 task（原来写死 G1） | 否则 RP1 的 ckpt 报 `CrossBackendIncompatibleError` |
| `render.py` | ① 从 scene 的 `<include>` 推导机器人 xml 与根刚体名；② `qpos[:36]` 改成按实际宽度切；③ 幽灵用专用半透明材质；④ 去掉共面地面并加 MSAA | RP1 的 MJCF 有自带地面、用 `material=` 上色、根刚体叫 `base_link` |
| `conf/.../task/{rp1,rpo}_super_mimic/*` | 新增 | 28/23 关节、`context_dim` 32/27、backend overlay |

---

## 关键坑（都踩过，详见 docs）

1. **RP1 的 MJCF 自带一个地面**，和 scene 的 `floor` 共面 → 渲染出波纹。只在渲染路径里内联
   去掉，物理不动（否则和训练时的动力学不一致）。
2. **`<position>` 执行器用 `forcerange`，不是 `ctrlrange`**：后者夹的是位置目标。
3. **mjwarp 不支持 `mjSOL_PGS`**，MJCF 必须 Newton/CG。
4. **RP1 的 `robot.xml` 自带 `<?xml?>` 声明**，内联进 scene 会变成文档中间的声明 → 解析失败。
5. **接 target 的末端关节拿不到参考**：RPO 的 `ankle_roll` 恒 0（foot task 挂在 pitch link 上）、
   RP1 的 `wrist_pitch` 恒 0（hand task 挂在 wrist_yaw 上）。影响小但要知道。
6. **`soft_limit_factor=0.9` 会和参考动作打架**：RPO 的参考有 83% 的帧踩在软限位外（G1 只有 40%）。
7. **position 执行器是 `gainprm=[kp,0,0]` / `biasprm=[0,-kp,-kv]`**，改增益时只改
   `biasprm[2]` 不改 `biasprm[1]` 会把伺服变成"弹回零位"，诊断脚本会给出完全错误的结论。
8. **GMR 的 `setup.py` 依赖 `smplx @ git+github`**，别 `pip install -e .`，直接加 `PYTHONPATH`。

---

## 算法要点（避免误读）

SuperMimic **不是 PPO**。策略梯度来自"在世界模型里想象 32 步、对策略做解析梯度"：
`loss = -(Σ γ^t·alive_t·r_t + γ^32·alive_32·V(s_32))`，梯度穿过世界模型回传。
critic 用同一套解析奖励做 λ-return 回归。真实数据只用来在线重训世界模型（Dyna）。
策略网络输出是**确定性**动作，没有 log_prob、没有重要性采样比、没有 clip。

奖励是一个写死的稠密模仿误差（14 个刚体的位置/朝向/线速度/角速度 + 根位姿，高斯核，
满载 5.0/步），yaml 里没有可调权重——三台机器人共用同一套常数。

---

## 授权

本仓库的补丁与脚本：MIT。但它依赖/派生于若干第三方项目，见 [THIRD_PARTY.md](THIRD_PARTY.md)：
Uni-SuperMimic（Motphys）、RoboParty GMR、RP1/RPO 描述包（CERN-OHL-W-2.0）、LAFAN1（Ubisoft）。
机器人网格与动作数据不在本仓库内，由脚本从原始来源获取。
