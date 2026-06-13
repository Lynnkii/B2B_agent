import os
from dotenv import load_dotenv
from openai import OpenAI
import chromadb

# ==========================================
# 1. 绝对路径配置与环境变量
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, ".env")
db_path = os.path.join(current_dir, "vector_db")

load_dotenv(env_path)
api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    raise ValueError(f"🚨 致命错误：未找到 API_KEY，请确保 {env_path} 存在且配置正确！")

# 全局初始化大模型客户端
llm_client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# ==========================================
# 2. 核心功能函数暴露给前端使用
# ==========================================

def get_vector_collection():
    """连接并获取本地 ChromaDB 向量数据库集群"""
    chroma_client = chromadb.PersistentClient(path=db_path)
    return chroma_client.get_collection(name="b2b_products")

def extract_intent(inquiry_text):
    """大模型：负责抽取复杂外贸邮件中的核心语义意图"""
    prompt = f"Extract the core product category/name the buyer is looking for from this inquiry. Output ONLY 1-3 English words, nothing else.\n\nInquiry:\n{inquiry_text}"
    response = llm_client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0 # 保持绝对冷静的意图提取
    )
    return response.choices[0].message.content.strip().replace(".", "").replace('"', '')

def generate_quote_email(user_inquiry, search_results, temperature=0.2):
    """大模型：基于 RAG 检索回来的真实业务数据，渲染合规的报价单"""
    
    # 组装 RAG Context (防止幻觉的核心屏障)
    context_str = "【系统自动召回的底层商业参数】：\n"
    for i in range(len(search_results['ids'][0])):
        meta = search_results['metadatas'][0][i]
        doc = search_results['documents'][0][i]
        context_str += f"- 产品名称: {meta['product_name']}\n  起订量: {meta['moq']}\n  阶梯价: {meta['price_tier']}\n  产品特征: {doc}\n\n"

    # 系统提示词
    system_prompt = f"""你是一个资深的 B2B 外贸业务员。请根据买家询盘，结合【系统自动召回的底层商业参数】，撰写专业英文报价邮件。
    ⚠️ 严禁幻觉：报价必须绝对遵守参数中的【阶梯价】和【起订量(MOQ)】。如果客户采购量未达到 MOQ，请专业委婉地拒绝或要求提量。
    {context_str}"""

    response = llm_client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"买家询盘：\n{user_inquiry}"}
        ],
        temperature=temperature
    )
    return response.choices[0].message.content