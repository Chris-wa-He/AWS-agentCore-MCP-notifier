# 项目沟通规则

## 语言使用规范

### 项目沟通
- **主要语言**: 中文
- 所有项目讨论、需求分析、设计文档等使用中文
- 代码审查和技术讨论使用中文
- 项目文档和说明文件使用中文

### 代码编写规范
- **代码语言**: 严格使用英文
- 变量名、函数名、类名必须使用英文
- 文件名和目录名使用英文
- 配置文件中的键值使用英文

#### ❌ 错误示例
```python
# 禁止使用中文命名
用户名 = "张三"
def 获取用户信息():
    pass

class 用户管理器:
    pass
```

#### ✅ 正确示例
```python
# 使用英文命名
username = "张三"
def get_user_info():
    pass

class UserManager:
    pass
```

### 代码注释规范
- **推荐**: 中英双语注释
- **可接受**: 纯中文注释
- **可接受**: 纯英文注释

#### 推荐的注释风格
```python
def calculate_user_score(user_data: dict) -> float:
    """
    计算用户评分 / Calculate user score
    
    Args:
        user_data: 用户数据字典 / User data dictionary
        
    Returns:
        float: 用户评分 / User score
    """
    # 验证输入数据 / Validate input data
    if not user_data:
        return 0.0
    
    # 计算基础分数 / Calculate base score
    base_score = user_data.get('base_points', 0)
    
    return base_score
```

## 文档规范

### 技术文档
- 使用中文编写
- 代码示例中的变量名使用英文
- API 文档可使用中英双语

### README 和项目说明
- 主要使用中文
- 如需国际化，可提供英文版本

### 错误信息和日志
- 用户面向的错误信息使用中文
- 开发调试日志可使用英文
- 系统日志建议使用英文

## 版本控制规范

### Git 提交信息
- **推荐**: 使用中文描述功能变更
- **可接受**: 使用英文（遵循 conventional commits）

#### 示例
```
feat: 添加用户认证功能
fix: 修复登录页面样式问题
docs: 更新 API 文档
```

### 分支命名
- 使用英文命名分支
- 遵循 git-flow 规范

#### 示例
```
feature/user-authentication
bugfix/login-style-issue
hotfix/security-patch
```

## 重要提醒

⚠️ **严格禁止在代码中使用中文标识符**
- 这会导致编码问题和跨平台兼容性问题
- 影响代码的国际化和维护性
- 违反 Python PEP 8 规范

✅ **推荐做法**
- 沟通使用中文，代码使用英文
- 注释可以中英双语，帮助理解
- 保持代码的专业性和国际化标准