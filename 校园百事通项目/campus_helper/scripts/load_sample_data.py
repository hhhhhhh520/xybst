"""
加载示例数据到知识库
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from services.knowledge_base import KnowledgeBaseService
from services.rag_retriever import Document


async def load_sample_data():
    """加载示例数据"""
    kb_service = KnowledgeBaseService()
    await kb_service.initialize()

    # 示例数据
    samples = [
        {
            "content": """图书馆开放时间

图书馆开放时间如下：
- 工作日（周一至周五）：7:00-22:00
- 周末（周六至周日）：8:00-21:00
- 法定节假日：9:00-17:00

进入图书馆需要刷校园卡。借书最多可借10本，借期30天。逾期还书每本每天收取0.1元滞纳金。""",
            "title": "图书馆开放时间",
            "source": "图书馆",
            "doc_type": "policy"
        },
        {
            "content": """奖学金评定办法

国家奖学金：8000元/年，申请条件：成绩排名专业前10%，无挂科记录，综合素质测评优秀。申请时间：每年9月。

国家励志奖学金：5000元/年，申请条件：家庭经济困难学生，成绩排名专业前30%，无挂科记录。申请时间：每年10月。

校级奖学金：一等奖3000元（专业前5%），二等奖2000元（专业前15%），三等奖1000元（专业前30%）。

申请流程：关注学院通知 → 准备材料（成绩单、获奖证书、个人事迹） → 参加评审 → 公示发放。""",
            "title": "奖学金评定办法",
            "source": "学工处",
            "doc_type": "policy"
        },
        {
            "content": """在读证明办理流程

线上申请：登录教务系统 → 证明申请 → 选择"在读证明" → 填写提交 → 等待审核（1-2工作日）。

现场办理：地点为行政楼教务处202室，时间为工作日8:30-11:30、14:00-17:00，需携带校园卡。

注意事项：在读证明免费办理；如需英文版需额外申请；委托他人代办需提供委托书和双方身份证复印件。""",
            "title": "在读证明办理流程",
            "source": "教务处",
            "doc_type": "process"
        },
        {
            "content": """成绩单打印流程

登录教务系统 → 成绩管理 → 成绩打印 → 选择学期 → 打印预览 → 确认无误后打印。

打印后需到教务处盖章才有效。地点：行政楼202室，时间：工作日8:30-11:30、14:00-17:00。

英文成绩单需额外申请，处理时间3-5个工作日。""",
            "title": "成绩单打印流程",
            "source": "教务处",
            "doc_type": "process"
        },
        {
            "content": """选课流程

选课时间：每学期第16-18周进行下学期选课。

选课步骤：
1. 登录教务系统
2. 进入【选课管理】→【网上选课】
3. 先选必修课，再选选修课
4. 确认选课结果

注意事项：热门课程需抢；选课冲突需调整；补选阶段可调整选课。""",
            "title": "选课流程",
            "source": "教务处",
            "doc_type": "process"
        },
        {
            "content": """宿舍报修流程

报修方式：
1. 扫描宿舍楼二维码在线报修
2. 拨打后勤服务热线：XXX-XXXXXXXX
3. 到宿管阿姨处登记

维修时间：一般问题24小时内处理，紧急问题2小时内响应。

常见问题：灯泡更换、门锁维修、空调故障、水管漏水等。""",
            "title": "宿舍报修流程",
            "source": "后勤处",
            "doc_type": "process"
        },
        {
            "content": """校园卡使用说明

校园卡功能：食堂消费、图书馆门禁、宿舍门禁、校内超市消费。

充值方式：
1. 微信/支付宝搜索"校园卡"小程序
2. 食堂自助充值机
3. 校园卡服务中心（行政楼1楼）

挂失：拨打服务热线或到服务中心办理，挂失后48小时内可解挂。

补办：携带身份证到校园卡服务中心，工本费15元。""",
            "title": "校园卡使用说明",
            "source": "后勤处",
            "doc_type": "policy"
        },
        {
            "content": """请假流程

请假类型：病假、事假、公假。

请假流程：
1. 填写请假申请表（辅导员处领取或教务系统下载）
2. 附相关证明材料（病假需医院证明）
3. 提交辅导员审批
4. 超过3天需学院审批
5. 超过7天需教务处审批

注意事项：请假期间需保持联系畅通；返校后及时销假。""",
            "title": "请假流程",
            "source": "学工处",
            "doc_type": "process"
        }
    ]

    print(f"正在加载 {len(samples)} 条示例数据...")

    for i, sample in enumerate(samples, 1):
        doc_id = await kb_service.add_document(
            content=sample["content"],
            title=sample["title"],
            source=sample["source"],
            doc_type=sample["doc_type"]
        )
        print(f"[{i}/{len(samples)}] 已添加: {sample['title']} (ID: {doc_id})")

    # 获取统计
    stats = await kb_service.get_stats()
    print(f"\n知识库统计: {stats}")

    print("\n示例数据加载完成!")


if __name__ == "__main__":
    asyncio.run(load_sample_data())
