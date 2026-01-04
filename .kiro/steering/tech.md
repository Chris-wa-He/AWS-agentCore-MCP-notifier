# 技术栈

## 核心技术

- **语言**: Python 3.8+
- **包管理器**: uv (替代 pip 和 virtualenv)
- **虚拟环境**: uv 管理的虚拟环境

## 开发工具

- **IDE**: VS Code (已配置)
- **代码格式化**: 推荐使用 black, isort
- **代码检查**: 推荐使用 ruff 或 flake8
- **类型检查**: 推荐使用 mypy

## 常用命令

### 环境管理
```bash
# 创建虚拟环境
uv venv

# 激活虚拟环境
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate     # Windows

# 安装依赖
uv pip install -r requirements.txt

# 添加新依赖
uv add package_name

# 同步依赖
uv sync
```

### 项目运行
```bash
# 在虚拟环境中运行 Python 脚本
uv run python script.py

# 在虚拟环境中运行模块
uv run python -m module_name

# 直接通过 uv 运行（推荐）
uv run script.py
```

### 测试
```bash
# 运行测试（使用 pytest）
uv run pytest

# 运行特定测试文件
uv run pytest tests/test_file.py

# 运行测试并生成覆盖率报告
uv run pytest --cov=src
```

## 重要规则

⚠️ **严禁在全局 Python 环境中直接运行项目代码**
- 所有代码执行必须在虚拟环境中进行
- 使用 `uv run` 命令确保在正确的环境中执行
- 避免使用 `python` 或 `pip` 命令，优先使用 `uv run python` 和 `uv pip`