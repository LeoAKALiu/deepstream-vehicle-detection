# Git 仓库设置说明

## 已完成

✅ Git仓库已初始化  
✅ .gitignore 已创建  
✅ .gitattributes 已创建  
✅ 初始提交已完成

## 配置远程仓库

### 1. 添加远程仓库

```bash
cd /home/liubo/Download/deepstream-vehicle-detection

# 添加远程仓库（替换为你的实际仓库URL）
git remote add origin <your-repository-url>

# 例如：
# git remote add origin https://github.com/your-username/your-repo.git
# 或
# git remote add origin git@github.com:your-username/your-repo.git
```

### 2. 查看远程仓库

```bash
git remote -v
```

### 3. 推送到远程仓库

```bash
# 首次推送
git push -u origin main

# 如果默认分支是 master
git push -u origin master

# 如果远程仓库为空，可能需要先创建分支
git branch -M main  # 重命名当前分支为 main
git push -u origin main
```

## 常用 Git 命令

### 查看状态

```bash
git status
git log --oneline
```

### 提交更改

```bash
# 添加所有更改
git add .

# 提交
git commit -m "描述你的更改"

# 推送到远程
git push
```

### 创建分支

```bash
# 创建新分支
git checkout -b feature/new-feature

# 切换分支
git checkout main

# 查看所有分支
git branch -a
```

### 查看差异

```bash
# 查看未暂存的更改
git diff

# 查看已暂存的更改
git diff --cached
```

## .gitignore 说明

已配置忽略以下文件/目录：

- Python缓存文件（`__pycache__/`, `*.pyc`）
- 日志文件（`*.log`, `logs/`）
- 数据库文件（`*.db`, `*.sqlite`）
- 模型文件（`models/*.engine`, `models/*.onnx`等）
- 录制文件（`recordings/`, `results/`）
- IDE配置文件（`.vscode/`, `.idea/`）
- 临时文件

## 注意事项

1. **敏感信息**：确保不要提交包含敏感信息的配置文件（如API密钥）
   - 如果 `config.yaml` 包含敏感信息，考虑使用环境变量或配置文件模板

2. **大文件**：模型文件（`.engine`, `.onnx`等）已被忽略
   - 如果需要版本控制，考虑使用 Git LFS

3. **数据库文件**：`detection_results.db` 已被忽略
   - 生产数据不应提交到仓库

4. **录制文件**：`recordings/` 和 `results/` 目录已被忽略
   - 这些是运行时生成的数据

## 推荐工作流程

1. **开发新功能**
   ```bash
   git checkout -b feature/feature-name
   # 进行开发
   git add .
   git commit -m "Add feature: feature-name"
   git push origin feature/feature-name
   ```

2. **修复Bug**
   ```bash
   git checkout -b fix/bug-description
   # 修复bug
   git add .
   git commit -m "Fix: bug-description"
   git push origin fix/bug-description
   ```

3. **合并到主分支**
   ```bash
   git checkout main
   git merge feature/feature-name
   git push origin main
   ```

## 标签管理

```bash
# 创建标签
git tag -a v1.0.0 -m "Release version 1.0.0"

# 推送标签
git push origin v1.0.0

# 查看所有标签
git tag
```

---

**创建时间**: 2024年12月8日  
**状态**: ✅ Git仓库已初始化并准备好推送


