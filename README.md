# NOF1.AI 项目

## 项目结构
- `backend/` - 后端服务 (FastAPI)
- `frontend/` - 前端界面 (React + Vite)

## 开发环境配置

### 后端配置
1. 创建虚拟环境:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. 配置环境变量:
   项目需要以下环境变量，请复制 `.env.example` 文件并根据您的配置进行修改：
   ```bash
   # 复制并修改 .env 文件
   cd backend
   cp .env.example .env
   # 编辑 .env 文件填入必要配置
   ```
   
   必需的环境变量包括：
   - `BINANCE_API_KEY` - Binance API密钥
   - `BINANCE_API_SECRET` - Binance API密钥
   - `DEEPSEEK_API_KEY` - DeepSeek API密钥
   - `CRON_SECRET_KEY` - 定时任务认证密钥

3. 运行后端服务:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### 前端配置
1. 安装依赖:
   ```bash
   cd frontend
   npm install
   ```

2. 运行开发服务器:
   ```bash
   npm run dev
   ```

## 部署说明

### 代码推送
已配置 `.gitignore` 排除依赖包，可直接推送源代码:
- 后端: 排除 `venv/`, `__pycache__/`
- 前端: 排除 `node_modules/`, `dist/`

### 生产环境部署
1. 后端:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. 前端:
   ```bash
   cd frontend
   npm install
   npm run build
   # 使用 nginx 或其他静态文件服务器部署 dist/ 目录
   ```