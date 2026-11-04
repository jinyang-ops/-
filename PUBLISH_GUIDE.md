# 将本机修改后的项目推送到自己的 GitHub 仓库

目标仓库：<https://github.com/jinyang-ops/->。仓库名是一个连字符，合法；HTTPS Git 地址为 `https://github.com/jinyang-ops/-.git`。

核对时该仓库已有 `main` 分支和初始化 README，不是完全空仓库。本指南建议先克隆目标仓库，再复制本机修改后的源码，避免无关历史合并，也避免带入上游约 750 MB 的文件及历史 SDK / 模型对象。原项目目录及其 Git 历史保留不变。

本指南中的源码复制和 Git 推送在你的 Ubuntu 上执行。文档、测试脚本和实测摘要已整理，完整训练源码及本机导出的日志报告以本机项目目录为准。

## 1. 将文档放入原项目目录

把本包的 `README.md`、`.gitignore`、`docs/`、`reports/` 和 `tests/` 合并到你修改后的原项目根目录，保留自己已有的脚本和源码修改；同名个人文件先对比或备份。使用本次实际测试记录，不把模拟报告作为实测结果。上游链接与来源说明应保留。

先进入本机项目；下面 `/path/to/...` 必须替换成真实路径：

```bash
cd /path/to/legged_robot_competition
git status --short
mkdir -p docs
git rev-parse HEAD > docs/source-base-commit.txt
```

`source-base-commit.txt` 记录复制前的 HEAD；未提交修改不在该 SHA 中，应在新仓库提交后另行记录新提交。该操作不会更改原仓库分支。

当前继续使用已能训练的项目代码，SDK 保持本机独立安装。`legged_gym/` 中的个人源码修改会复制到新仓库，SDK 通过官方渠道获取。如果确有额外 SDK 定制依赖，需在发布前单独记录其最小补丁和应用说明。

## 2. 克隆目标仓库，复制源码

从上一步的原项目根目录执行。`../quadruped-test-portfolio` 应是一个尚不存在的目录：

```bash
git clone -- https://github.com/jinyang-ops/-.git ../quadruped-test-portfolio

# 如未安装 rsync：sudo apt-get install rsync
# 不使用 --delete，也不复制原仓库 .git。
rsync -a \
  --exclude='.git' \
  --exclude='isaacgym/' \
  --exclude='logs/' \
  --exclude='log/' \
  --exclude='runs/' \
  --exclude='wandb/' \
  --exclude='events.out.tfevents.*' \
  --exclude='*.pt' \
  --exclude='*.pth' \
  --exclude='*.ckpt' \
  --exclude='*.onnx' \
  --exclude='*.safetensors' \
  --exclude='__pycache__/' \
  --exclude='*.so' \
  --exclude='*.so.*' \
  --exclude='.venv/' \
  --exclude='venv/' \
  --exclude='/env/' \
  --exclude='.env' \
  --exclude='.env.*' \
  ./ ../quadruped-test-portfolio/

cd ../quadruped-test-portfolio
git remote -v
```

此时 `origin` 应指向 `jinyang-ops/-.git`。原上游的旧历史不会进入这个仓库，源码、必要资产及许可证会复制过来；个人来源记录和 README 承担溯源说明。新仓库原有的 README 会被本次提供的 README 内容覆盖，旧版本仍保留在 Git 历史中。

这里故意不复制本机 SDK、权重和大日志。它们仍在原目录中；若要在新目录运行，需按 README 安装 SDK，模型可从原目录通过明确路径加载。

## 3. 验证忽略规则与暂存内容

```bash
# 这些示例路径即使不存在，也应匹配忽略规则。
git check-ignore --no-index -v \
  logs/example.txt \
  legged_gym/logs/rough_go2/example.txt \
  model_5000.pt \
  tests/__pycache__/batch_test.cpython-38.pyc \
  isaacgym/python/isaacgym/terrain_utils.py

git status --short
git add -A
git diff --cached --stat
git diff --cached -- README.md .gitignore docs/troubleshooting.md

# 应无输出；rg 无匹配时退出码为 1，属于正常结果。
git ls-files | rg '(^|/)(logs|log|__pycache__)/|\.(pt|pth|ckpt|onnx|safetensors)$|^isaacgym/'
```

若自己已有脚本路径为根目录 `batch_test.py`，请对比并保留个人修改，同步调整 README 路径；本次提供的脚本逻辑测试与本机 GPU 集成测试应分开记录。检查新增源码、配置、脚本、必要资产及原许可证是否齐全。

注意：`.gitignore` 只阻止未跟踪文件被默认添加。它不会把原仓库已跟踪文件或历史里的模型自动清除；`git add -f` 也能绕过规则。本指南使用干净导出流程，避免将这些旧对象带入新仓库。

若在其他既有仓库中仅需取消跟踪而保留本地文件，可以先用 `git ls-files` 检查，再对确认的路径执行 `git rm --cached`；该操作仍不会清除历史对象。

## 4. 提交与推送

确认上一步的暂存区内容正确后执行：

```bash
git commit -m "docs: add quadruped reproduction and testing portfolio"
git push -u origin main
```

若提示作者身份未设置，在本仓库设置自己的名字和邮箱，再重新提交：

```bash
git config user.name "你的 GitHub 显示名"
git config user.email "你的 GitHub 邮箱或 noreply 邮箱"
```

HTTPS 推送需要 GitHub 支持的凭据方式，不能使用账户密码。已安装 GitHub CLI 时，可使用 `gh auth login` 和 `gh auth setup-git`；也可使用凭据管理器或配置好的 SSH。不要把访问令牌写进 URL、源码或文档。

如果推送提示远程已有新提交，先 `git fetch origin` 查看变化，再按实际情况 `git pull --rebase origin main`，解决冲突后继续推送，不使用强制覆盖。

## 5. 推送后核验

```bash
git status --short
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

本地 HEAD 应与远程 `main` SHA 一致，工作区应无待提交修改。打开目标页面确认 README 渲染、相对链接、测试脚本和许可证正常，且目录中没有 logs、SDK、权重及缓存。

如后续重命名仓库，再按新地址更新 `origin` 和 README 链接；当前的 `-` 名称不影响上述操作。
