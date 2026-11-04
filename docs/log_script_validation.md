# 日志脚本验证记录

本包的 batch_test.py 独立运行，只依赖 Python 标准库与 TensorBoard。无需 Isaac Gym 或 PyTorch。

- 已执行环境：临时 Python 3.12 / TensorBoard 2.14.0 / NumPy 1.26.4。
- 已通过：6 项独立逻辑测试，覆盖窗口与峰值分离、空值和非有限值、重复 / 回退 step、配置可比性保护、真实格式合成事件读写与 CSV / Markdown 报告。
- 语法目标：Python 3.8，已进行相应语法解析检查；用户的实际 Python 3.8 环境运行结果待真实日志导出后记录。
- 测试数据为合成夹具，不代表机器人实测结果。

需要复测工具逻辑时执行：

```bash
python -m unittest discover -s tests -p test_batch_test.py -v
```

本包不包含地图修复工具，也不要求追加高并发或多种子模型评测。当前工作范围为 1024 环境训练、前段演示与日志摘要。
