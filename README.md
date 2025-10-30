# NOF1.AI 项目部署说明

## 项目结构
- `backend/` - 后端代码 (FastAPI)
- `frontend/` - 前端代码 (React + Vite)

## 已完成的步骤

1. 创建了 `.gitignore` 文件，排除了依赖包：
   - 后端：`venv/`, `__pycache__/`, `*.pyc`
   - 前端：`node_modules/`, `dist/`
   - 其他：`.env`, `.vscode/`, 日志文件等

2. 将所有代码添加到本地Git仓库并进行了首次提交

3. 配置了远程仓库地址

## 推送代码到GitHub的步骤

由于需要身份验证，您需要选择以下一种方式：

### 方式一：使用GitHub Personal Access Token（推荐）
```bash
cd /root/nof1.ai
git remote set-url origin https://<your-token>@github.com/gongjixiaobai/nof1.ai.git
git push -u origin master
```

### 方式二：使用SSH密钥
1. 复制公钥：
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```

2. 在GitHub网站上添加此公钥到您的账户：
   - 访问 GitHub > Settings > SSH and GPG keys > New SSH key
   - 粘贴公钥内容并保存

3. 使用SSH方式推送：
   ```bash
   cd /root/nof1.ai
   git remote set-url origin git@github.com:gongjixiaobai/nof1.ai.git
   git push -u origin master
   ```