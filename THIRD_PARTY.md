# 第三方组件与授权

本仓库只包含"粘合层"：补丁、配置、资产适配脚本、诊断脚本、渲染脚本。
机器人网格、动作数据、上游框架都不在这里，由脚本从原始来源获取。

| 组件 | 来源 | 授权 | 本仓库如何使用 |
|---|---|---|---|
| Uni-SuperMimic | https://github.com/Motphys/Uni-SuperMimic | 见上游仓库 | `patches/` 覆盖其中 10 个文件；不复制其余代码 |
| GMR（含 IK-CONFIG 自动生成） | https://github.com/Roboparty/GMR ，fork 自 https://github.com/YanjieZe/GMR | MIT | `gmr_patches/` 覆盖 3 个文件；不复制其余代码 |
| RP1 描述包（`rp1_description`） | https://github.com/Roboparty/rp1_description | CERN-OHL-W-2.0 | `scripts/setup/01_fetch_assets.sh` 下载；网格不进仓库 |
| RPO 描述包（`rpo_description`） | https://github.com/Roboparty/rpo_description | CERN-OHL-W-2.0 | 同上 |
| LAFAN1 动作数据 | Ubisoft La Forge，https://github.com/ubisoft/ubisoft-laforge-animation-dataset | Ubisoft 许可（研究用途） | `scripts/setup/04_fetch_motions.sh` 从镜像下载；不进仓库 |
| Unitree G1 模型 | Uni-SuperMimic 自带 | 见上游 | 未修改 |
| MuJoCo / mujoco_warp / UniLab | Google DeepMind / UniLab | Apache-2.0 等 | 依赖 |

## 注意

- RP1/RPO 的网格是 **CERN-OHL-W-2.0**（弱互惠硬件许可）：修改再分发需要遵循其条款。
  本仓库只放我们自己改的 **MJCF**（执行器、solver、keyframe），网格保持原样由脚本获取。
- LAFAN1 数据仅限研究/非商业用途，重定向产物（40 段 CSV）属于其衍生数据，因此也没有放进仓库。
- 如果要把本仓库的补丁合并回上游，请先看上游的贡献流程。

本仓库自身的内容（补丁、脚本、文档）以 MIT 授权。
