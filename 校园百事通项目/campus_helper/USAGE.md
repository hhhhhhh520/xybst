# 校园百事通 - 使用说明

## 快速启动

### 1. 启动后端服务

```bash
# 进入项目目录
cd campus_helper

# 激活虚拟环境
venv\Scripts\activate

# 启动后端
python backend/main.py
```

看到 `Uvicorn running on http://0.0.0.0:8000` 表示启动成功。

### 2. 打开前端界面

直接用浏览器打开 `frontend/index.html` 文件。

或者访问 http://localhost:8000 查看API文档。

## 功能说明

### 支持的问题类型

1. **政策咨询**
   - "图书馆开放时间"
   - "奖学金怎么申请"
   - "国家奖学金条件"

2. **办事流程**
   - "在读证明怎么办理"
   - "成绩单怎么打印"
   - "选课流程是什么"

3. **校园生活**
   - "宿舍报修"
   - "校园卡使用"
   - "请假流程"

### 快速回复按钮

前端界面提供了常用问题的快捷按钮，点击即可快速提问。

## API接口

### 对话接口

**POST** `/api/chat`

请求体：
```json
{
    "message": "图书馆开放时间",
    "session_id": "session_123",
    "user_id": "user_456"
}
```

响应：
```json
{
    "answer": "图书馆开放时间如下...",
    "type": "knowledge_qa",
    "sources": [{"title": "图书馆开放时间"}]
}
```

### 知识库搜索

**GET** `/api/knowledge/search?query=图书馆&top_k=5`

### 系统状态

**GET** `/api/system/health`

## 添加知识

### 方式一：运行示例数据脚本

```bash
python scripts/load_sample_data.py
```

### 方式二：通过API添加

```bash
curl -X POST http://localhost:8000/api/knowledge/documents \
  -H "Content-Type: application/json" \
  -d "{\"content\":\"文档内容\",\"title\":\"标题\",\"source\":\"来源\",\"doc_type\":\"policy\"}"
```

## 配置说明

编辑 `.env` 文件配置API密钥：

```env
# LLM提供商: openai, anthropic, local
LLM_PROVIDER=openai

# OpenAI配置
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-3.5-turbo
```

## 常见问题

### Q: 后端启动报错？

检查是否安装了所有依赖：
```bash
pip install -r requirements.txt
```

### Q: 前端无法连接后端？

1. 确认后端已启动
2. 检查端口8000是否被占用
3. 查看浏览器控制台错误信息

### Q: 回答不准确？

1. 检查知识库是否有相关内容
2. 尝试换种方式提问
3. 添加更多相关知识到知识库

## 项目结构

```
campus_helper/
├── backend/          # 后端代码
│   ├── api/         # API路由
│   ├── services/    # 核心服务
│   └── main.py      # 启动入口
├── frontend/        # 前端界面
│   └── index.html
├── scripts/         # 工具脚本
├── data/            # 数据文件
└── tests/           # 测试代码
```

## 技术支持

- API文档: http://localhost:8000/docs
- 项目进度: PROJECT_PROGRESS.md
