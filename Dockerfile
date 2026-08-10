FROM python:3.13-slim

WORKDIR /app

# 系统依赖（scikit-learn 编译需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ /app/

# 复制前端构建产物
COPY frontend/dist/ /app/frontend/dist/

# 初始化数据库
RUN python -c "from database import init_db, seed_categories; init_db(); seed_categories()"

# 环境变量：静态文件路径
ENV STATIC_DIR=/app/frontend/dist

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
