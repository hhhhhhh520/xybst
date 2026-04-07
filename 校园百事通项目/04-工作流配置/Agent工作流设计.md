# 校园百事通智能体 - Agent工作流设计

## 一、工作流总体架构

### 1.1 工作流分类

```
校园百事通智能体
├── 核心工作流
│   ├── 智能问答工作流（信息咨询）
│   ├── 个性化查询工作流（课表/成绩）
│   ├── 事务办理向导工作流（流程引导）
│   └── 多轮对话管理工作流（上下文管理）
├── 工具工作流
│   ├── 教务查询工作流
│   ├── 天气查询工作流
│   └── 计算工具工作流
└── 特殊处理工作流
    ├── 兜底答复工作流
    ├── 转人工工作流
    └── 异常处理工作流
```

### 1.2 工作流调度逻辑

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  意图识别节点                                                  │
│  - 分类：知识问答 / 个人查询 / 事务办理 / 闲聊 / 其他          │
│  - 置信度：高(>0.8) / 中(0.5-0.8) / 低(<0.5)                  │
└─────────────────────────────────────────────────────────────┘
    │
    ├─ 知识问答 ──→ 智能问答工作流
    │
    ├─ 个人查询 ──→ 个性化查询工作流
    │
    ├─ 事务办理 ──→ 事务办理向导工作流
    │
    ├─ 闲聊 ──────→ 闲聊回复
    │
    └─ 其他/置信度低 ──→ 澄清追问 / 兜底答复
```

---

## 二、核心工作流详细设计

### 2.1 智能问答工作流

**适用场景**：用户提出校园信息咨询类问题

**Coze工作流配置**：

```yaml
工作流名称: 智能问答工作流
工作流ID: qa_workflow
触发条件: 意图识别为"知识问答"

节点配置:
  - 节点ID: start
    节点类型: 开始节点
    输出参数:
      - user_input: 用户输入文本
      - user_id: 用户ID
      - session_id: 会话ID

  - 节点ID: extract_params
    节点类型: 大模型节点
    功能: 提取用户身份信息和查询意图
    提示词: |
      从用户输入中提取以下信息：
      - 用户身份（学生/教师）
      - 查询主题（教务/学工/后勤等）
      - 具体问题类型

      用户输入：{{user_input}}

      以JSON格式输出提取结果。
    输出参数:
      - user_type: 用户身份
      - topic: 查询主题
      - question_type: 问题类型

  - 节点ID: check_knowledge
    节点类型: 知识库检索节点
    功能: 从知识库检索相关信息
    配置:
      知识库: 校园百事通知识库
      召回数量: 5
      相似度阈值: 0.75
      重排序: 开启
    输入参数:
      - query: "{{user_input}}"
    输出参数:
      - retrieved_docs: 检索结果列表
      - retrieval_score: 最高相似度分数

  - 节点ID: judge_sufficient
    节点类型: 条件判断节点
    功能: 判断检索结果是否足够回答问题
    条件:
      - 条件1: retrieval_score >= 0.75 且 retrieved_docs不为空
        跳转: generate_answer
      - 条件2: 0.5 <= retrieval_score < 0.75
        跳转: rewrite_query
      - 条件3: retrieval_score < 0.5 或 retrieved_docs为空
        跳转: fallback_response

  - 节点ID: rewrite_query
    节点类型: 大模型节点
    功能: 重写查询，扩展同义词
    提示词: |
      用户原始查询：{{user_input}}

      请重写查询，扩展同义词和相关表达，以提高检索准确率。
      输出3个不同的查询变体。
    输出参数:
      - rewritten_queries: 重写后的查询列表
    后续: 重新执行check_knowledge节点

  - 节点ID: generate_answer
    节点类型: 大模型节点
    功能: 基于检索结果生成答案
    提示词: |
      你是校园百事通小百，请基于以下检索结果回答用户问题。

      用户问题：{{user_input}}

      检索结果：
      {{retrieved_docs}}

      回答要求：
      1. 直接回答用户问题
      2. 标注信息来源
      3. 如有不确定，明确说明
      4. 提供下一步操作建议
    输出参数:
      - answer: 生成的答案
      - sources: 引用来源

  - 节点ID: format_output
    节点类型: 代码节点
    功能: 格式化输出，添加引用标记
    代码: |
      def main(answer: str, sources: list) -> dict:
          formatted = answer + "\n\n📚 信息来源：\n"
          for i, src in enumerate(sources, 1):
              formatted += f"[{i}] {src['title']}\n"
          return {"final_answer": formatted}
    输出参数:
      - final_answer: 格式化后的答案

  - 节点ID: fallback_response
    节点类型: 大模型节点
    功能: 生成兜底答复
    提示词: |
      用户问题：{{user_input}}

      知识库中没有找到相关信息，请生成一个友好的兜底答复：
      1. 表示歉意
      2. 说明可能的原因
      3. 提供替代方案（相关部门联系方式、建议查询渠道）
    输出参数:
      - fallback_answer: 兜底答复

  - 节点ID: end
    节点类型: 结束节点
    输入参数:
      - answer: "{{final_answer}}" 或 "{{fallback_answer}}"
```

**工作流流程图**：

```
[开始] → [参数提取] → [知识库检索]
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         [相似度高]      [相似度中]       [相似度低]
              │               │               │
              ▼               ▼               ▼
      [生成答案] ←← [查询重写] →→      [兜底答复]
              │       ↗
              ▼      /
      [格式化输出]
              │
              ▼
          [结束]
```

### 2.2 个性化查询工作流

**适用场景**：用户查询个人相关信息（课表、成绩等）

```yaml
工作流名称: 个性化查询工作流
工作流ID: personal_query_workflow
触发条件: 意图识别为"个人查询"

节点配置:
  - 节点ID: start
    节点类型: 开始节点

  - 节点ID: check_auth
    节点类型: 条件判断节点
    功能: 检查用户是否已绑定学工号
    条件:
      - 已绑定: 跳转 parse_intent
      - 未绑定: 跳转 guide_binding

  - 节点ID: guide_binding
    节点类型: 大模型节点
    功能: 引导用户绑定身份
    提示词: |
      用户想要查询个人信息，但尚未绑定学工号。
      请友好地引导用户完成绑定，说明绑定步骤。
    输出参数:
      - binding_guide: 绑定指引
    后续: 结束工作流

  - 节点ID: parse_intent
    节点类型: 大模型节点
    功能: 解析查询意图和参数
    提示词: |
      用户输入：{{user_input}}

      识别查询类型和参数：
      - 查询类型：课表/成绩/考试/学分
      - 时间参数：本学期/上学期/具体学期
      - 其他参数：如周次等

      以JSON格式输出。
    输出参数:
      - query_type: 查询类型
      - semester: 学期
      - week: 周次（可选）

  - 节点ID: validate_params
    节点类型: 代码节点
    功能: 校验参数完整性
    代码: |
      def main(query_type: str, semester: str) -> dict:
          missing = []
          if not semester:
              missing.append("学期")
          return {
              "is_valid": len(missing) == 0,
              "missing_params": missing
          }
    输出参数:
      - is_valid: 参数是否完整
      - missing_params: 缺失参数列表

  - 节点ID: ask_missing
    节点类型: 大模型节点
    功能: 询问缺失参数
    提示词: |
      用户想要查询{{query_type}}，但缺少以下信息：{{missing_params}}
      请生成追问语句，友好地询问用户。
    输出参数:
      - clarification: 追问语句
    后续: 等待用户回复，返回validate_params

  - 节点ID: call_edu_api
    节点类型: 插件节点
    功能: 调用教务系统API
    插件: campus_edu_query
    接口: 根据query_type选择
      - 课表: get_schedule
      - 成绩: get_grades
      - 考试: get_exams
    输入参数:
      - student_id: "{{user_id}}"
      - query_type: "{{query_type}}"
      - semester: "{{semester}}"
      - week: "{{week}}"
    输出参数:
      - raw_data: API返回的原始数据

  - 节点ID: process_data
    节点类型: 代码节点
    功能: 处理API返回数据
    代码: |
      def main(raw_data: dict, query_type: str) -> dict:
          if query_type == "课表":
              # 按星期几分组
              schedule = {}
              for course in raw_data['courses']:
                  day = course['day_of_week']
                  if day not in schedule:
                      schedule[day] = []
                  schedule[day].append(course)
              return {"processed": schedule, "type": "schedule"}

          elif query_type == "成绩":
              # 计算GPA，标注挂科
              grades = raw_data['grades']
              total_score = 0
              total_credit = 0
              failed = []
              for g in grades:
                  if g['score'] < 60:
                      failed.append(g['course_name'])
                  total_score += g['score'] * g['credit']
                  total_credit += g['credit']
              gpa = total_score / total_credit / 10 - 5 if total_credit > 0 else 0
              return {
                  "processed": grades,
                  "gpa": round(gpa, 2),
                  "failed": failed,
                  "type": "grades"
              }

          return {"processed": raw_data, "type": query_type}
    输出参数:
      - processed_data: 处理后的数据
      - data_type: 数据类型

  - 节点ID: generate_response
    节点类型: 大模型节点
    功能: 生成自然语言回复
    提示词: |
      用户查询：{{query_type}}
      处理后的数据：{{processed_data}}

      请将数据转化为自然、易懂的口语化表达。
      如果是课表，按时间顺序列出；
      如果是成绩，突出GPA和挂科科目（如有）。
    输出参数:
      - response: 生成的回复

  - 节点ID: end
    节点类型: 结束节点
```

### 2.3 事务办理向导工作流

**适用场景**：用户需要办理某项事务，需要流程指导

```yaml
工作流名称: 事务办理向导工作流
工作流ID: guide_workflow
触发条件: 意图识别为"事务办理"

节点配置:
  - 节点ID: start
    节点类型: 开始节点

  - 节点ID: identify_affair
    节点类型: 大模型节点
    功能: 识别具体事务类型
    提示词: |
      用户输入：{{user_input}}

      识别用户想要办理的事务类型：
      - 奖学金申请
      - 证明开具
      - 请假
      - 转专业
      - 其他

      同时提取用户当前所处的阶段（如刚开始/准备材料/办理中）。
    输出参数:
      - affair_type: 事务类型
      - current_stage: 当前阶段

  - 节点ID: retrieve_guide
    节点类型: 知识库检索节点
    功能: 检索办事指南
    配置:
      知识库: 办事指南知识库
      召回数量: 3
    输入参数:
      - query: "{{affair_type}}办理流程"

  - 节点ID: determine_stage
    节点类型: 条件判断节点
    功能: 根据用户阶段确定输出内容
    条件:
      - current_stage == "刚开始": 跳转 show_overview
      - current_stage == "准备材料": 跳转 show_materials
      - current_stage == "办理中": 跳转 show_current_step

  - 节点ID: show_overview
    节点类型: 大模型节点
    功能: 展示整体流程概览
    提示词: |
      事务类型：{{affair_type}}
      办事指南：{{retrieved_guide}}

      请生成整体流程概览，包括：
      1. 办理步骤（分步骤列出）
      2. 大致时间安排
      3. 重要提醒

      最后询问用户想了解哪一步的详细信息。

  - 节点ID: show_materials
    节点类型: 大模型节点
    功能: 展示所需材料清单
    提示词: |
      生成{{affair_type}}所需的材料清单，使用checkbox格式，
      并说明每份材料的获取方式。

  - 节点ID: show_current_step
    节点类型: 大模型节点
    功能: 展示当前步骤详情
    提示词: |
      用户目前在办理{{affair_type}}，请：
      1. 询问用户当前具体进展
      2. 针对该步骤提供详细指导
      3. 告知下一步该做什么

  - 节点ID: save_state
    节点类型: 变量节点
    功能: 保存对话状态
    配置:
      保存变量:
        - affair_type
        - current_stage
        - last_response

  - 节点ID: end
    节点类型: 结束节点
```

### 2.4 多轮对话管理工作流

**适用场景**：复杂问题需要多轮交互澄清

```yaml
工作流名称: 多轮对话管理工作流
工作流ID: multi_turn_workflow
触发条件: 需要维护对话上下文

节点配置:
  - 节点ID: start
    节点类型: 开始节点

  - 节点ID: load_context
    节点类型: 变量节点
    功能: 加载对话历史状态
    配置:
      读取变量:
        - dialog_state: 对话状态
        - filled_slots: 已填充槽位
        - pending_confirmation: 待确认信息

  - 节点ID: update_state
    节点类型: 大模型节点
    功能: 更新对话状态
    提示词: |
      对话历史：{{dialog_history}}
      当前输入：{{user_input}}
      当前状态：{{dialog_state}}
      已填充槽位：{{filled_slots}}

      分析当前输入，更新对话状态：
      1. 提取新的槽位信息
      2. 识别用户意图变化
      3. 判断是否需要确认

      输出更新后的状态（JSON格式）。
    输出参数:
      - new_state: 新状态
      - new_slots: 新填充的槽位
      - need_confirmation: 是否需要确认

  - 节点ID: check_completion
    节点类型: 条件判断节点
    功能: 检查槽位是否填满
    条件:
      - 槽位已满且无需确认: 跳转 execute_action
      - 槽位未满: 跳转 ask_slot
      - 需要确认: 跳转 confirm_info

  - 节点ID: ask_slot
    节点类型: 大模型节点
    功能: 询问缺失槽位
    提示词: |
      还缺少以下信息：{{missing_slots}}
      请生成自然的追问语句，一次只问一个最重要的问题。

  - 节点ID: confirm_info
    节点类型: 大模型节点
    功能: 向用户确认信息
    提示词: |
      请向用户确认以下理解是否正确：
      {{pending_confirmation}}

      等待用户确认后再继续。

  - 节点ID: execute_action
    节点类型: 跳转节点
    功能: 执行对应操作
    配置:
      根据intent跳转到对应工作流:
        - 知识问答 → qa_workflow
        - 个人查询 → personal_query_workflow
        - 事务办理 → guide_workflow

  - 节点ID: save_context
    节点类型: 变量节点
    功能: 保存更新后的状态

  - 节点ID: end
    节点类型: 结束节点
```

---

## 三、工具工作流设计

### 3.1 教务查询工作流

```yaml
工作流名称: 教务查询工作流
功能: 封装教务系统查询插件

输入参数:
  - student_id: 学号
  - query_type: 查询类型
  - semester: 学期（可选）
  - week: 周次（可选）

处理逻辑:
  1. 调用 campus_edu_query 插件
  2. 根据 query_type 选择接口:
     - schedule → get_schedule
     - grades → get_grades
     - exams → get_exams
  3. 处理返回数据，格式化输出
  4. 错误处理（网络异常、无数据等）

输出参数:
  - success: 是否成功
  - data: 查询结果
  - error_msg: 错误信息（如有）
```

### 3.2 天气查询工作流

```yaml
工作流名称: 天气查询工作流
功能: 查询校园所在地天气

输入参数:
  - city: 城市名称（默认学校所在城市）
  - date: 日期（今天/明天/后天）

处理逻辑:
  1. 调用天气查询插件
  2. 解析返回数据
  3. 生成自然语言描述

输出参数:
  - weather_desc: 天气描述
  - temperature: 温度
  - suggestion: 出行建议
```

---

## 四、特殊处理工作流

### 4.1 兜底答复工作流

```yaml
触发条件:
  - 知识库检索无结果
  - 用户意图不明确
  - 置信度低于阈值

处理流程:
  1. 记录未回答的问题
  2. 生成友好的兜底回复：
     - 表示歉意
     - 说明原因
     - 提供替代方案（相关部门联系方式）
  3. 询问是否需要转人工

回复模板:
  "抱歉，这个问题我暂时不太确定 😅\n\n"
  "建议您：\n"
  "1. 咨询{{相关部门}}，电话：{{电话}}\n"
  "2. 前往{{办公地点}}现场咨询\n"
  "3. 查看学校官网：{{网址}}\n\n"
  "需要我帮您转接人工服务吗？"
```

### 4.2 转人工工作流

```yaml
触发条件:
  - 用户主动要求转人工
  - 连续3轮未解决问题
  - 涉及敏感投诉

处理流程:
  1. 汇总对话历史
  2. 记录用户问题类型
  3. 生成转接提示：
     - 告知用户正在转接
     - 提供预计等待时间
     - 建议用户准备好相关信息
  4. 将对话记录传递给人工客服系统

输出:
  - 转接成功提示
  - 对话摘要（供人工客服参考）
```

### 4.3 异常处理工作流

```yaml
异常类型及处理:

1. 插件调用失败:
   - 重试3次
   - 仍失败则返回："系统暂时繁忙，请稍后再试"
   - 记录错误日志

2. 知识库检索超时:
   - 返回简化答复（基于缓存）
   - 后台异步完成检索
   - 记录性能问题

3. 生成内容违规:
   - 触发内容安全过滤
   - 返回："这个问题我暂时无法回答"
   - 记录并人工审核

4. 用户输入异常:
   - 空输入：提示"请输入您的问题"
   - 超长输入：截断并提示"问题太长，请精简"
   - 乱码/特殊字符：提示"输入格式有误"
```

---

## 五、工作流配置最佳实践

### 5.1 节点命名规范

```
命名格式：[动作]_[对象]_[序号]

示例：
- extract_params_01    # 提取参数节点
- check_auth_01        # 检查认证节点
- generate_answer_01   # 生成答案节点
```

### 5.2 变量命名规范

```
输入变量：input_[名称]      例：input_user_id
输出变量：output_[名称]     例：output_answer
中间变量：[模块]_[名称]     例：retrieval_docs
全局变量：global_[名称]     例：global_user_info
```

### 5.3 错误处理规范

- 每个节点都应考虑失败情况
- 设置合理的超时时间（一般5-10秒）
- 错误信息要友好，不要暴露技术细节
- 记录错误日志，便于排查

### 5.4 性能优化建议

- 合理使用缓存，避免重复调用
- 异步处理非关键路径
- 控制知识库召回数量，减少Token消耗
- 使用条件判断减少不必要的节点执行

---

## 六、工作流测试用例

### 6.1 智能问答工作流测试

| 用例ID | 输入 | 预期流程 | 预期输出 |
|--------|------|----------|----------|
| QA-001 | "图书馆几点开门？" | 参数提取→知识检索→生成答案 | 准确的开放时间 |
| QA-002 | "奖学金怎么申请？"（模糊） | 参数提取→知识检索→重写查询→生成答案 | 详细的申请流程 |
| QA-003 | "学校附近哪家火锅好吃？" | 参数提取→知识检索→兜底答复 | 友好的超出范围提示 |

### 6.2 个性化查询工作流测试

| 用例ID | 输入 | 用户状态 | 预期流程 | 预期输出 |
|--------|------|----------|----------|----------|
| PQ-001 | "我这学期课表" | 已绑定 | 检查认证→解析意图→调用API→生成回复 | 个人课表 |
| PQ-002 | "我成绩怎么样" | 未绑定 | 检查认证→引导绑定 | 绑定指引 |
| PQ-003 | "明天有什么课" | 已绑定 | 检查认证→解析意图→追问学期→调用API | 追问学期 |

---

## 七、Coze平台配置指南

### 7.1 创建工作流步骤

1. 登录Coze平台，进入"工作流"模块
2. 点击"创建工作流"
3. 填写工作流名称和描述
4. 从左侧拖拽节点到画布
5. 配置每个节点的参数
6. 连接节点，形成完整流程
7. 保存并测试

### 7.2 节点配置截图说明

（此处可插入Coze平台配置截图）

### 7.3 调试技巧

1. 使用"单步调试"功能，逐个节点检查
2. 查看每个节点的输入输出
3. 使用测试数据验证流程
4. 记录执行时间和Token消耗

---

**文档维护人**：[姓名]
**最后更新**：2025年X月X日
**版本**：V1.0
