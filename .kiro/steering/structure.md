# 项目结构

## 标准 Python 项目组织

```
project/
├── .venv/                  # uv 创建的虚拟环境（不提交到版本控制）
├── src/                    # 主要源代码目录
│   └── package_name/       # 主包目录
│       ├── __init__.py
│       ├── main.py         # 入口文件
│       └── modules/        # 子模块
├── tests/                  # 测试代码
│   ├── __init__.py
│   ├── test_main.py
│   └── conftest.py         # pytest 配置
├── docs/                   # 文档
├── scripts/                # 辅助脚本
├── .kiro/                  # Kiro 配置
│   └── steering/           # 项目指导规则
├── .vscode/                # VS Code 配置
├── .gitignore              # Git 忽略文件
├── pyproject.toml          # 项目配置和依赖
├── uv.lock                 # 锁定的依赖版本
└── README.md               # 项目说明
```

## 目录说明

### `/src`
- 包含所有生产代码
- 使用包结构组织代码
- 每个包都应有 `__init__.py` 文件

### `/tests`
- 镜像 `src/` 的结构
- 测试文件以 `test_` 开头
- 使用 pytest 作为测试框架

### `/docs`
- 项目文档
- API 文档
- 使用指南

### `/scripts`
- 构建脚本
- 部署脚本
- 数据处理脚本

## 命名约定

### 文件和目录
- 使用小写字母和下划线：`my_module.py`
- 包名使用小写：`mypackage`
- 测试文件：`test_module_name.py`

### Python 代码
- 类名使用 PascalCase：`MyClass`
- 函数和变量使用 snake_case：`my_function`
- 常量使用大写：`MAX_SIZE`
- 私有成员以下划线开头：`_private_method`

## 配置文件

### `pyproject.toml`
- 项目元数据和依赖管理
- 工具配置（black, ruff, mypy 等）
- 构建系统配置

### `.gitignore`
必须包含：
```
.venv/
__pycache__/
*.pyc
*.pyo
*.egg-info/
.pytest_cache/
.coverage
.mypy_cache/
```

## 最佳实践

- 所有 Python 文件应包含适当的 docstring
- 使用类型注解提高代码可读性
- 保持模块职责单一
- 遵循 PEP 8 代码风格指南
- 编写单元测试覆盖核心功能