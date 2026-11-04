# GO2 四足机器人强化学习训练与仿真测试

**Ubuntu 22.04 · Isaac Gym · PyTorch · RSL-RL / PPO · Python**

基于开源 GO2 控制项目的独立部署、训练复现与测试作品集。重点展示环境兼容性排查、并行仿真负载测试、训练监控和日志分析。模型展示与人工验收范围限定地图前段。

控制框架与 PPO 实现来自上游，个人工作集中在复现、调试、测试和实验整理。本项目未开展实机部署或全地图通关验证。

## 实测结果

| 项目 | 本次结果 |
| --- | --- |
| 正式训练 | 1024 个并行环境，6000 次迭代 |
| 总采样步数 | 294,912,000 |
| 训练退出码 | 0 |
| 上游训练计时 | 6448.08 s，约 107.47 分钟 |
| 末轮 Mean reward | 29.81 |
| 末轮 Mean episode length | 1144.98 step |
| 末轮 rew_tracking_lin_vel | 1.6774 |
| 已确认模型 | model_5000.pt、model_6000.pt |

这些数据来自本次训练终端输出。tracking 指标是加权且归一化的奖励，不是准确率；末轮值不是全程平均值。模型实际行走表现另行回放记录。

完整证据与状态见 [实际测试记录](reports/test_report.2026-11-04.md) 和 [正式训练摘要 CSV](reports/formal_training_summary.csv)。

## 测试目标与工作内容

| 方向 | 工作与验收 | 当前状态 |
| --- | --- | --- |
| 环境兼容性 | 定位 Python 动态库加载失败，核对实际 SDK 路径、CUDA 和依赖 | 导入检查通过 |
| 接口兼容性 | 对照 stairs_terrain 的实际签名适配项目调用 | 当前版本可训练；展示范围为地图前段 |
| 冒烟测试 | 64 环境、50 次迭代，核对步数与模型保存 | 模型和事件日志已生成 |
| 负载测试 | 256 / 512 / 1024 环境短时运行并采集显存 | 统计已记录；1024 档退出码为 0 |
| 正式训练 | 1024 环境完成 6000 次 PPO 更新 | 步数、退出码及模型保存通过 |
| 日志自动化 | 提取目标 scalar、窗口统计、峰值及末值，生成 CSV / Markdown | 已解析本次训练的 6000 条记录并导出报告；6 项脚本逻辑测试通过 |
| 模型演示 | 加载 model_6000.pt 检查地图前段运动 | 用户反馈能持续向前行走；演示视频待补 |

## 并行负载测试结果

| 环境数 | 迭代数 | 总采样步数 | 训练计时 s | 末轮吞吐 steps/s | 设备显存采样峰值 MiB |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 256 | 200 | 2,457,600 | 125.93 | 20,522 | 4,274 |
| 512 | 200 | 4,915,200 | 172.20 | 27,770 | 4,446 |
| 1024 | 200 | 9,830,400 | 259.78 | 33,136 | 4,892 |

显存约每秒采样一次，包含桌面等其他进程；采样峰值不是进程独占显存或瞬时峰值。吞吐为末轮日志值。各档回报不用于评价并发数对学习质量的因果影响。详细数据见 [负载摘要](reports/load_test_summary.csv)。

## 环境

| 组件 | 已确认版本 |
| --- | --- |
| 系统 | Ubuntu 22.04.5 LTS |
| GPU | NVIDIA GeForce RTX 4060 系列，8188 MiB 显存 |
| NVIDIA 驱动 | 595.91.07 |
| Python | 3.8.20 |
| PyTorch / 自带 CUDA 运行时 | 2.4.1+cu121 / 12.1 |
| NumPy / TensorBoard | 1.23.5 / 2.14.0 |
| Isaac Gym | 本机 NVIDIA SDK；实际路径与签名已记录，具体 Preview 版本待补 |
| RSL-RL / legged_gym | 项目对应源码安装 |

Ubuntu 22.04 是本次实测部署环境，不替代 SDK 的官方支持说明。nvidia-smi 显示的 CUDA 支持上限与 PyTorch 自带 CUDA 运行时是不同信息。

## 安装与兼容性排错

从 NVIDIA 官方渠道获取匹配 SDK，按设备驱动选择兼容 PyTorch。已有跑通环境可复用，本机组件采用 editable 安装：

```bash
conda create -n legged_robot_parkour python=3.8 -y
conda activate legged_robot_parkour
python -m pip install torch==2.4.1 torchvision==0.19.1 --index-url https://download.pytorch.org/whl/cu121
python -m pip install numpy==1.23.5 tensorboard==2.14.0 protobuf==4.25.3
python -m pip install -e /path/to/isaacgym/python
python -m pip install -e ./rsl_rl
python -m pip install -e ./legged_gym
python -m pip check
```

### libpython3.8.so.1.0 加载失败

本次库文件实际存在，加入当前进程的动态库搜索路径后导入成功：

```bash
ls -l "$CONDA_PREFIX"/lib/libpython3.8.so*
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
python -c 'import isaacgym; import torch; print(torch.__version__, torch.cuda.is_available())'
```

库不存在时先修复 Python 环境，不跨 Python ABI 伪造软链接。保持 Isaac Gym 先于 PyTorch 导入。

### TensorBoard MessageToJson 报错

TensorBoard 2.14.0 与较新版 protobuf 可能发生 including_default_value_fields 参数不兼容。提供的处理方案是在对应环境固定兼容版本并重启 TensorBoard：

```bash
python -m pip install protobuf==4.25.3
python -m pip check
```

最终安装版本另行归档。Git 证书链、SDK 接口等排查过程见 [排查日志](docs/troubleshooting.md)。Git HTTPS 应保持证书验证启用，组织代理场景需核实并配置正确的 CA。

## 训练与监控

以下命令从项目根目录执行，沿用当前训练配置：

```bash
python legged_gym/legged_gym/scripts/train.py \
  --task=go2 --num_envs=1024 --headless --max_iterations=6000 \
  --experiment_name=portfolio_front --run_name=front1024

tensorboard --logdir=legged_gym/logs/portfolio_front \
  --host=127.0.0.1 --port=6006
```

监控 Train/mean_reward、Train/mean_episode_length 和 Episode/rew_tracking_lin_vel。本次末轮回报为 29.81，不将“6000 次策略崩溃”写为当前实验结论。

## 模型回放

权重和原始日志留在本地。先完成训练或恢复对应运行目录，再执行回放；其他运行使用其实际目录名。

```bash
python legged_gym/legged_gym/scripts/play.py \
  --task=go2 --num_envs=1 --experiment_name=portfolio_front \
  --load_run=Nov04_18-09-44_front1024_20261104_180939 \
  --checkpoint=6000
```

本次用户已确认 6000 检查点在地图前段能持续向前行走，视频待归档。比较 5000 / 6000 检查点时，保持相同配置并分别记录；训练曲线点不是独立模型评测结果。

本仓库包含 GO2 所需的 URDF 与 7 个网格文件。其他机型的配置保留自上游，其机器人资产需从上游另行获取。

## 自动化日志分析

tests/batch_test.py 为单文件工具，只依赖标准库与 TensorBoard，读取已有日志：

```bash
python tests/batch_test.py \
  --log-root legged_gym/logs/portfolio_front \
  --tag Episode/rew_tracking_lin_vel --window=100 \
  --output reports/tracking_report.md
```

输出 Markdown 与 CSV：末尾窗口均值和总体标准差、训练日志峰值与末值。空目录、缺失 tag、非有限值、重复 / 回退 step、点数不足会标记异常。默认命令只提取摘要；跨 run 的阈值比较需要配置可比性证据。

本次实际导出结果见 [速度跟踪奖励报告](reports/tracking_report.md)：

| 项目 | 结果 |
| --- | ---: |
| 有效记录数 | 6000 |
| 末尾窗口 step | 5900–5999 |
| 窗口均值 ± 总体标准差 | 1.349064 ± 0.533320 |
| 全程日志峰值 / step | 1.840597 / 5915 |
| 末值 / step | 1.677412 / 5999 |

这些是训练日志统计，不将峰值所在 step 自动认定为最佳模型版本。

该脚本不加载模型。退出码 0=摘要生成或比较通过，1=指标退化，2=输入或证据问题。

## 数据管理与来源

提交源码、脚本、小体积 CSV、截图与报告；SDK、原始 logs、权重和缓存留在本地。gitignore 覆盖任意层级的 logs/、*.pt 和 __pycache__/，已跟踪文件需另外处理。

- 主项目：[jindadu00/legged_robot_competition](https://github.com/jindadu00/legged_robot_competition)
- 参考项目：[Training-Quadruped-Robots-to-Traverse-Diverse-Complex-Terrains](https://github.com/jindadu00/Training-Quadruped-Robots-to-Traverse-Diverse-Complex-Terrains)
- 本仓库：[jinyang-ops/-](https://github.com/jinyang-ops/-)

保留上游代码、资产与依赖的许可证。SDK 按官方许可获取使用，不将上游算法、控制框架或机器人模型标为个人原创。
