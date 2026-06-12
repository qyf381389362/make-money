import os
import re
import json
import logging
from typing import Tuple, Dict, Any
import httpx

# 设置日志记录
logger = logging.getLogger("gemini_service")

# 允许的决策心理分类
MOTIVATION_TYPES = ["追涨杀跌", "贪婪", "恐慌", "理性分析", "其它"]


def extract_json_content(text: str) -> Dict[str, Any]:
    """
    顽固提取文本中的 JSON 部分并解析。
    支持去除 Markdown 的 ```json 块标记，或者通过正则提取第一个匹配的大括号 {} 内容。
    """
    text = text.strip()
    
    # 尝试直接解析整个文本
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试匹配 ```json ... ``` 块中的内容
    markdown_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if markdown_match:
        try:
            return json.loads(markdown_match.group(1))
        except json.JSONDecodeError:
            pass

    # 通过最外层大括号匹配 JSON
    braces_match = re.search(r"\{[\s\S]*\}", text)
    if braces_match:
        try:
            return json.loads(braces_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError("无法解析出 JSON 结构")


def audit_decision(
    symbol: str, action: str, shares: float, price: float, reason: str
) -> Tuple[str, str]:
    """
    使用 Gemini-1.5-flash 对决策日记进行心理审计。
    返回元组: (motivation_type, ai_audit)
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("未检测到环境变量 GEMINI_API_KEY，自动降级为默认审计结果")
        return "其它", "未配置 AI 审计服务 (环境变量 GEMINI_API_KEY 缺失)"

    prompt = (
        f"请作为专业的投资心理学与行为金融学专家，对以下用户的交易决策进行心理审计和点评：\n"
        f"交易标的：{symbol}\n"
        f"交易方向：{'买入' if action == 'buy' else '卖出'}\n"
        f"交易数量：{shares}\n"
        f"交易价格：{price}\n"
        f"用户自述的交易原因：\n\"\"\"\n{reason}\n\"\"\"\n\n"
        f"要求：\n"
        f"1. 识别并对该次交易进行心理偏差归类。只允许归为以下 5 类之一：\n"
        f"   - \"追涨杀跌\": 看到涨了忍不住追买，或者跌了恐慌性砍仓。\n"
        f"   - \"贪婪\": 在高位因为渴望更多收益而盲目加仓或不愿止盈。\n"
        f"   - \"恐慌\": 因为害怕进一步下跌而在没有明确逻辑的情况下卖出。\n"
        f"   - \"理性分析\": 有明确的估值支撑、商业逻辑或资产配置计划，且交易符合既定纪律。\n"
        f"   - \"其它\": 无法归入上述分类的决策心理状态。\n"
        f"2. 给出 150 字以内的专业、中肯的行为审计评语（ai_audit）。\n"
        f"3. 必须以 JSON 格式输出，结构为：\n"
        f'{{"motivation_type": "心理偏差类别", "ai_audit": "详细点评评语"}}'
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    # 构造要求模型以结构化 JSON 返回的 payload
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "motivation_type": {
                        "type": "STRING",
                        "enum": MOTIVATION_TYPES
                    },
                    "ai_audit": {
                        "type": "STRING"
                    }
                },
                "required": ["motivation_type", "ai_audit"]
            }
        }
    }

    try:
        # 设置 30 秒超时，防止生成速度慢导致 ReadTimeout
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            res_data = response.json()
            
            candidates = res_data.get("candidates", [])
            if not candidates:
                raise ValueError("Gemini 接口未返回有效的候选内容 (candidates 为空)")
                
            content_text = candidates[0]["content"]["parts"][0]["text"]
            parsed = extract_json_content(content_text)
            
            motivation_type = parsed.get("motivation_type")
            ai_audit = parsed.get("ai_audit")
            
            if motivation_type not in MOTIVATION_TYPES:
                motivation_type = "其它"
                
            return motivation_type, ai_audit
            
    except Exception as e:
        logger.exception(f"Gemini API 决策审计失败: {str(e)}")
        # 超时或报错时进行优雅的降级处理，将类型标记为“其它”，评语中说明失败信息
        err_msg = f"AI 审计失败 (由于 {type(e).__name__})"
        return "其它", err_msg
