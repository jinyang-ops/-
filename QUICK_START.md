# 训练完成后的收尾步骤

本包包含本次实测 README、排查日志、测试报告、简历描述和单文件日志分析脚本。将包内文档及脚本合并到现有项目中，继续使用当前训练源码。

## 1. 导出真实日志摘要

确认 tests/batch_test.py 已放入项目后，在 Ubuntu 执行：

```bash
cd /home/yang/legged_robot_competition
conda activate legged_robot_parkour
python tests/batch_test.py \
  --log-root legged_gym/logs/portfolio_front \
  --tag Episode/rew_tracking_lin_vel \
  --window=100 --output reports/tracking_report.md
cat reports/tracking_report.md
```

默认命令只做摘要提取，不要求修改训练代码或补做实验。输出 tracking_report.md 与 tracking_report.csv。报告中的峰值是训练日志点，不自动认定为最佳模型。将输出发回，补齐本机真实日志验证记录。

也可导出训练回报：

```bash
python tests/batch_test.py \
  --log-root legged_gym/logs/portfolio_front \
  --tag Train/mean_reward --window=100 \
  --output reports/reward_report.md
```

## 2. 归档前段演示

使用本次 model_6000.pt 回放，录制约 20–30 秒前段行走，保留模型编号和实际观察说明。已收到的人工反馈为“能持续向前行走”；不把它写为全地图通过率或实机性能。

## 3. 发布作品集

按 PUBLISH_GUIDE.md 将本机修改后的源码与本包文件合并推送到 https://github.com/jinyang-ops/- 。日志、权重、SDK 和缓存留在本地，保留上游许可证。简历文本见 docs/resume_project.md。
