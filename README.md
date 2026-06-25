 一、项目概述
 
ToolForge 是一个自进化工具 AI Agent 框架。核心突破：Agent 在执行任务时自主感知工具缺失，实时生成代码创造新工具，通过 Docker 安全沙盒验证后入库，使工具库持续进化。

二、快速上手

```powershell
# 1. 设置 API Key
set DEEPSEEK_API_KEY=sk-你的key

# 2. 安装
cd 项目路径
pip install -e ".[dev]"

# 3. 测试
pytest tests/ -v

# 4. 构建沙盒镜像（首次）
python -c "from toolforge.sandbox.image_builder import ImageBuilder; ImageBuilder().build(force=True)"

# 5. 运行任务
python -m toolforge.cli "你的任务描述"

