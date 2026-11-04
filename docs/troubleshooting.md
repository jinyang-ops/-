# 环境与训练排查日志

当前范围为 GO2 仿真训练与测试，以地图前段行走作为展示及人工验收范围。未回传的数据不补写为已验证结果。

## ENV-001：Python 动态库加载失败

- 现象：Isaac Gym 导入时报 libpython3.8.so.1.0 无法打开。
- 定位：Python 3.8.20 对应的库文件及软链接存在，动态链接器未在当时的路径中找到它。
- 处理：激活 legged_robot_parkour，将当前环境的 lib 加入 LD_LIBRARY_PATH。
- 验证：SDK 与 PyTorch 成功导入，PyTorch 为 2.4.1+cu121、CUDA 12.1，CUDA available=True。随后完成 6000 次训练。
- 边界：当前终端设置已验证，随 Conda 激活自动设置未单独记录。

```bash
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
```

## API-001：地形函数接口不一致

- 初始复现经历包含 stairs_terrain 参数不匹配 TypeError，通过堆栈与签名定位。
- 本次确认实际 SDK 签名为 terrain、step_width、step_height，当前项目调用使用这三个参数。
- 当前版本可完成训练。后段地形高度语义不纳入本次验收，保留当前可运行版本，展示限定地图前段。

## TB-001：MessageToJson 参数不兼容

- 现象：MessageToJson 不接受 including_default_value_fields 参数。
- 分析：TensorBoard 2.14.0 与较新版 protobuf 的 API 可能不兼容。
- 提供方案：固定 protobuf 4.25.3，再重启 TensorBoard。
- 状态：正式训练完成；TensorBoard 最终安装版本与修复输出未单独归档。

```bash
python -m pip install protobuf==4.25.3
python -m pip check
```

## LOAD-001：并行仿真负载筛查

- 方法：256 / 512 / 1024 环境，各 200 次迭代，显存约每秒采样一次。
- 设备显存峰值：4274 / 4446 / 4892 MiB，包含桌面等其他进程。
- 已确认：1024 档步数 9830400、退出码 0，回传的关键词扫描摘要未出现匹配行。
- 待归档：256 / 512 档退出码、完整告警扫描与 GPU 型号。
- 判定：按当轮配置记录短时测试结果。PxgAABBManager 告警应保留完整文本定位，不直接等同于显存不足。本次不将“发生并修复 AABB 溢出”作为已验证成果。

## TRAIN-001：正式训练验收

- 配置：1024 环境，6000 次迭代，沿用当前项目配置。
- 结果：退出码 0，总采样 294912000 步，训练计时 6448.08 s。
- 末轮：Mean reward 29.81，Mean episode length 1144.98 step，rew_tracking_lin_vel 1.6774。
- 产物：model_5000.pt 和 model_6000.pt 存在。
- 结论：训练与保存链路通过。本次末轮数据不支持记录为“6000 次策略崩溃”。曲线峰值、窗口统计与前段回放另行记录。

## NET-001：Git HTTPS 证书问题

初始复现经历包含证书链问题，本次未回传完整错误与最终配置。排查系统时间、CA 包、组织代理根证书及 Git 独立 CA 设置，保持 TLS 校验启用；使用 git -c http.sslVerify=true ls-remote 验证。没有对应证据时不虚构本轮复测结论。
