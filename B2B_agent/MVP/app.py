import streamlit as st
import pandas as pd
from openai import OpenAI
import os
from dotenv import load_dotenv

# ==========================================
# 1. 基础配置与环境变量
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, ".env")
csv_path = os.path.join(current_dir, "products.csv")

load_dotenv(env_path)
api_key = os.getenv("DEEPSEEK_API_KEY")
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# ==========================================
# 2. Session State 状态管理 (防止页面刷新数据丢失)
# ==========================================
if "extracted_keyword" not in st.session_state:
    st.session_state.extracted_keyword = ""
if "current_step" not in st.session_state:
    st.session_state.current_step = 1

# ==========================================
# 3. 网页 UI 全局设置
# ==========================================
st.set_page_config(page_title="AI Sales Co-Pilot", page_icon="🤖", layout="wide")
st.title("🤖 智能接单 Agent")
st.divider()

# 工具函数：大模型提取搜索词
def extract_keyword_from_inquiry(inquiry_text):
    prompt = f"你是一个意图分析专家。请从下面这封买家询盘中，提取出他想采购的核心商品名称（提取最核心的1-2个英文单词即可，绝对不要多废话）。\n\n买家询盘：\n{inquiry_text}"
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0 
    )
    return response.choices[0].message.content.strip().replace(".", "").replace('"', '')

# ==========================================
# 4. 核心交互动线（双栏布局）
# ==========================================
col1, col2 = st.columns([1, 1.2], gap="large")

# ----------------- 左栏：用户操作区 -----------------
with col1:
    st.subheader("📥 步骤 1：商机录入与意图确认")
    
    default_inquiry = "Hi, I am an importer from Europe. I am looking for some fashion dresses for the upcoming summer season. I want to buy 300 pieces. Can you quote me the best price?"
    user_inquiry = st.text_area("📨 粘贴海外买家的原始询盘:", value=default_inquiry, height=180)
    
    # 动作 1：触发 AI 提取
    if st.button("🔍 1. AI 自动提取核心意图"):
        if not api_key:
            st.error("❌ 严重错误：未读取到 DEEPSEEK_API_KEY")
            st.stop()
        with st.spinner("🧠 AI 正在阅读长邮件..."):
            keyword = extract_keyword_from_inquiry(user_inquiry)
            st.session_state.extracted_keyword = keyword
            st.session_state.current_step = 2 # 推进到第二步
            
    # 当完成了第一步后，才显示第二步的 UI (体现交互动线)
    if st.session_state.current_step >= 2:
        st.info("💡 AI 已提取买家意图。如不准确，您可以在下方直接**手动修改**！")
        
        # 动作 2：人工确认或修改（核心亮点！）
        final_keyword = st.text_input("✍️ 确认搜索关键词 (Human-in-the-Loop):", value=st.session_state.extracted_keyword)
        
        temperature = st.slider("🎛️ AI 创造力调节 (Temperature)", min_value=0.0, max_value=1.0, value=0.2)
        
        generate_btn = st.button("🚀 2. 确认无误，生成报价单", type="primary", use_container_width=True)

# ----------------- 右栏：AI 输出与数据 -----------------
with col2:
    st.subheader("📤 步骤 2：知识库检索与回信生成")
    
    # 只有点击了最终的生成按钮，才执行后续逻辑
    if st.session_state.current_step >= 2 and 'generate_btn' in locals() and generate_btn:
        
        try:
            df = pd.read_csv(csv_path)
        except FileNotFoundError:
            st.error("❌ 找不到 products.csv！")
            st.stop()

        # 思考步骤 1：检索
        search_failed = False
        with st.status(f"🔍 正在知识库中匹配关键词: '{final_keyword}'...", expanded=True) as status:
            matched_products = df[
                df['product_name'].str.contains(final_keyword, case=False, na=False) | 
                df['core_features'].str.contains(final_keyword, case=False, na=False)
            ].head(2)
            
            if matched_products.empty:
                status.update(label=f"本地数据库匹配失败: '{final_keyword}'", state="error", expanded=False)
                search_failed = True
            else:
                st.success(f"命中 {len(matched_products)} 款相关商品！")
                st.dataframe(matched_products[['product_name', 'moq', 'price_tier']])
                status.update(label="RAG 知识库检索成功", state="complete", expanded=False)

        if search_failed:
            st.error(f"⚠️ **未找到与 '{final_keyword}' 相关的商品。**\n\n请在左侧修改关键词后重试，或转接人工客服。")
            st.stop() 

        # 思考步骤 2：生成
        context_str = "【真实商品参数与商业约束】：\n"
        for _, row in matched_products.iterrows():
            context_str += f"- 产品名称: {row['product_name']}\n  核心特征: {row['core_features']}\n  起订量: {row['moq']}\n  阶梯价: {row['price_tier']}\n\n"

        system_prompt = f"""你是一个资深的 B2B 外贸业务员。请根据买家询盘，结合【真实商品参数】，写一封极其专业的英文回信。
        ⚠️ 业务红线：1. 严格遵守阶梯价和起订量。2. 提取特征吸引客户。3. 结尾加入反问句。
        {context_str}"""

        with st.spinner("✍️ 正在生成严谨的商务报价邮件..."):
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"买家询盘：\n{user_inquiry}"}
                ],
                temperature=temperature 
            )
            final_email = response.choices[0].message.content

        st.markdown("### ✉️ 最终智能回复草稿")
        st.info(final_email)

        st.markdown("---")
        st.write("📊 **数据反馈 (RLHF)**")
        f_col1, f_col2, _ = st.columns([1, 1, 2])
        f_col1.button("👍 采纳")
        f_col2.button("👎 报错")