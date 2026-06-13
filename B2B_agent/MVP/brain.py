import pandas as pd
from openai import OpenAI
import os
from dotenv import load_dotenv

# 1. 核心修复：获取当前脚本所在的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. 强制指定去当前文件夹下寻找 .env 和 products.csv
env_path = os.path.join(current_dir, ".env")
csv_path = os.path.join(current_dir, "products.csv")

# 加载环境变量
load_dotenv(env_path)
api_key = os.getenv("DEEPSEEK_API_KEY")

# 拦截兜底：检查 API Key 是否真的读到了
if not api_key:
    print(f"❌ 严重错误：未获取到 API Key！")
    print(f"请确保在 {current_dir} 文件夹下创建了 .env 文件，并且里面写了 DEEPSEEK_API_KEY=你的真实Key")
    exit(1)

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

def mvp_rag_response(user_inquiry, keyword):
    print(f"🔍 正在从真实数据库中匹配关键词: '{keyword}'...")
    
    # 3. 使用绝对路径读取真实的 CSV 数据
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        return f"❌ 找不到数据库文件，请先运行 data_fetch.py 生成数据！"
    
    # 精准检索：只要品名或者描述里带这个词，就抓取出来
    matched_products = df[
        df['product_name'].str.contains(keyword, case=False, na=False) | 
        df['core_features'].str.contains(keyword, case=False, na=False)
    ].head(2) 
    
    if matched_products.empty:
        return "⚠️ 未在数据库找到商品，请更换关键词。"
        
    print(f"✅ 成功命中 {len(matched_products)} 款相关商品，交由 AI 生成回信...")
    print("-" * 50)
    
    # 组装安全的业务 Context
    context_str = "【真实商品参数与商业约束】：\n"
    for _, row in matched_products.iterrows():
        context_str += f"- 产品名称: {row['product_name']}\n"
        context_str += f"  核心特征: {row['core_features']}\n"
        context_str += f"  起订量(MOQ): {row['moq']}\n"
        context_str += f"  阶梯批发价: {row['price_tier']}\n\n"

    # 产品经理的极严 Prompt (提示词)
    system_prompt = f"""你是一个资深的 B2B 外贸业务员。
请根据买家询盘，结合下面检索到的【真实商品参数】，写一封极其专业的英文回信。

⚠️ B2B 业务红线：
1. 【零幻觉】：报价必须严格复制商品参数里的【阶梯批发价】和【起订量】，哪怕客户要求的数量少于MOQ，你也必须坚持原则，坚决不允许私自编造价格！
2. 【突显专业】：从商品特征中提取1-2个卖点作为安抚。
3. 【Call to Action】：邮件结尾设置一个专业问句，引导继续磋商。

{context_str}"""

    # 调用 API
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"买家发来的原始询盘：\n{user_inquiry}"}
        ],
        temperature=0.2 
    )
    return response.choices[0].message.content

# ==========================================
# 🚀 智能自适应测试运行 MVP
# ==========================================
if __name__ == "__main__":
    import pandas as pd
    
    # 自动读取你拉下来的真实数据库
    df_test = pd.read_csv(csv_path)
    # 获取第一个真实的商品名称
    first_product_name = df_test.iloc[0]['product_name']
    # 提取商品名的第一个单词作为搜索关键词
    search_keyword = str(first_product_name).split()[0] 
    
    print(f"💡 [自适应测试] 自动读取到了您的真实商品：{first_product_name}")
    print(f"💡 提取检索关键词：{search_keyword}\n")
    
    # 自动生成匹配这个商品的真实测试询盘
    test_inquiry = f"Hi, I am an importer from Europe. I am interested in your {first_product_name}. I want to buy 300 pieces. Can you quote me the best price?"
    
    # 跑通 AI 核心！
    final_email = mvp_rag_response(test_inquiry, search_keyword)
    print("\n📩 Agent 生成的最终回信：\n")
    print(final_email)