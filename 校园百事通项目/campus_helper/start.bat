@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==========================================
echo    校园百事通 - 启动脚本
echo ==========================================
echo.

:: 激活虚拟环境
call venv\Scripts\activate

:: 检查 .env 文件
if not exist .env (
    echo [警告] 未找到 .env 文件，使用默认配置
    echo 建议复制 .env.example 为 .env 并配置API密钥
    echo.
)

:: 创建必要目录
if not exist data\raw_docs mkdir data\raw_docs
if not exist data\knowledge_base mkdir data\knowledge_base
if not exist logs mkdir logs

echo [1/2] 正在启动后端服务...
echo      访问 http://localhost:8000/docs 查看API文档
echo.

:: 启动后端服务
start "校园百事通后端" cmd /k "venv\Scripts\python backend\main.py"

:: 等待后端启动
timeout /t 3 /nobreak >nul

echo [2/2] 正在打开前端界面...
echo.

:: 打开前端
start frontend\index.html

echo ==========================================
echo    启动完成！
echo    后端: http://localhost:8000
echo    前端: frontend/index.html
echo ==========================================
echo.
pause
