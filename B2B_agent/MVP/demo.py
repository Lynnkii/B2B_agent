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
# 2. 网页 UI 全局设置 (宽屏展示模式)
# ==========================================
st.set_page_config(page_title="AI Sales Co-Pilot Demo", page_icon="🚀", layout="wide")

# ==========================================
# 3. 侧边栏：面试“提词器”与全局设置
# ==========================================
with st.sidebar:
    st.image("https://img.alicdn.com/tfs/TB13DQPRFXXXXXGAPXXXXXXXXXX-330-94.png", width=150) # 放个阿里的Logo拉近距离
    st.markdown("### 👨‍💻 AI PM Demo 看板")
    st.markdown("---")
    st.markdown("**🎯 解决痛点**\n- 跨语种长尾询盘响应慢\n- 业务员查阅阶梯价易出错\n- 纯AI极易产生“报价幻觉”")
    st.markdown("**🧠 核心产品架构**\n1. **Intent LLM**: 意图抽取降噪\n2. **HITL**: 人机协同防错阻断\n3. **RAG Base**: 本地真实商业约束\n4. **Action LLM**: 极速生成报价单")
    st.markdown("---")
    temperature = st.slider("🎛️ AI 创造力调节 (Temperature)", 0.0, 1.0, 0.2, help="0.2适合严谨的商业报价")
    
    if st.button("🔄 重置演示状态", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ==========================================
# 4. Session State 状态管理
# ==========================================
if "current_step" not in st.session_state:
    st.session_state.current_step = 1
if "extracted_keyword" not in st.session_state:
    st.session_state.extracted_keyword = ""

st.title("🤖 B2B 智能接单 Agent")
st.markdown("##### 🚀 演示模式 (Human-in-the-Loop 人机协同架构)")
st.divider()

# 工具函数：大模型提取搜索词
def extract_keyword_from_inquiry(inquiry_text):
    prompt = f"你是一个意图分析专家。请从下面这封买家询盘中，提取出他想采购的核心商品名称（提取最核心的1-2个英文单词即可，例如 Dress, Cabinet，绝对不要多废话）。\n\n买家询盘：\n{inquiry_text}"
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0 
    )
    return response.choices[0].message.content.strip().replace(".", "").replace('"', '')

# ==========================================
# 5. 核心演示动线（双栏布局）
# ==========================================
col1, col2 = st.columns([1, 1.2], gap="large")

# ----------------- 左栏：商机录入与 HITL -----------------
with col1:
    st.subheader("📥 步骤 1：商机解析 (HITL)")
    
    # 【亮点】预设场景，一键切换演示
    scenarios = {
        "👗 场景 1：标准服装询盘": "Hi, I am an importer from Europe. I am looking for some fashion dresses for the upcoming summer season. I want to buy 300 pieces. Can you quote me the best price?",
        "🪑 场景 2：带特征要求的家居询盘": "Hello, we are a retailer in Dubai. We need tall narrow bathroom cabinets. Quantity is around 400. Do you support water-resistant finish? Send me CIF price.",
        "✍️ 场景 3：自定义手动输入": ""
    }
    selected_scenario = st.selectbox("⚡ 快速选择演示场景：", list(scenarios.keys()))
    
    # 当切换场景时，如果当前步骤大于1，重置状态避免错乱
    if "last_scenario" not in st.session_state:
        st.session_state.last_scenario = selected_scenario
    if selected_scenario != st.session_state.last_scenario:
        st.session_state.current_step = 1
        st.session_state.extracted_keyword = ""
        st.session_state.last_scenario = selected_scenario
        st.rerun()

    user_inquiry = st.text_area("📨 海外买家原始询盘:", value=scenarios[selected_scenario], height=150)
    
    # 动作 1：触发 AI 提取
    if st.session_state.current_step == 1:
        if st.button("🔍 1. 让 AI 自动提取核心意图", type="primary", use_container_width=True):
            if not api_key:
                st.error("❌ 严重错误：未读取到 API Key")
                st.stop()
            with st.spinner("🧠 正在调用 Intent LLM 解析长文本..."):
                keyword = extract_keyword_from_inquiry(user_inquiry)
                st.session_state.extracted_keyword = keyword
                st.session_state.current_step = 2
                st.rerun() # 刷新UI进入第二步
            
    # 第一步完成后，进入 HITL 人工确认环节
    if st.session_state.current_step >= 2:
        st.success("✨ AI 意图提取完成！已进入人机协同(HITL)确认环节。")
        final_keyword = st.text_input("✍️ 业务员确认/修改搜索词 (防止AI抓错词导致报价失误):", value=st.session_state.extracted_keyword)
        
        generate_btn = st.button("🚀 2. 确认无误，下发 RAG 并生成报价", type="primary", use_container_width=True)

# ----------------- 右栏：知识库与生成 -----------------
with col2:
    st.subheader("📤 步骤 2：防幻觉检索与生成")
    
    if st.session_state.current_step >= 2 and 'generate_btn' in locals() and generate_btn:
        try:
            df = pd.read_csv(csv_path)
        except FileNotFoundError:
            st.error("❌ 找不到 products.csv！")
            st.stop()

        # 思考步骤 1：检索
        search_failed = False
        with st.status(f"🔍 正在私有 RAG 知识库中匹配: '{final_keyword}'...", expanded=True) as status:
            matched_products = df[
                df['product_name'].str.contains(final_keyword, case=False, na=False) | 
                df['core_features'].str.contains(final_keyword, case=False, na=False)
            ].head(2)
            
            if matched_products.empty:
                status.update(label=f"本地数据库匹配失败: '{final_keyword}'", state="error", expanded=False)
                search_failed = True
            else:
                st.write(f"✅ 命中 {len(matched_products)} 款相关商品！已强行绑定阶梯价规则：")
                st.dataframe(matched_products[['product_name', 'moq', 'price_tier']])
                status.update(label="RAG 知识库检索成功，已锚定底线参数", state="complete", expanded=False)

        if search_failed:
            st.error(f"⚠️ **风控拦截！**\n\n系统未找到与 '{final_keyword}' 相关的商品，无法提供报价。\n\n**处理建议：**请在左侧修改关键词重新搜索，或将此疑难询盘转接人工客服处理。")
            st.stop() 

        # 思考步骤 2：生成
        context_str = "【真实商品参数与商业约束】：\n"
        for _, row in matched_products.iterrows():
            context_str += f"- 产品名称: {row['product_name']}\n  核心特征: {row['core_features']}\n  起订量: {row['moq']}\n  阶梯价: {row['price_tier']}\n\n"

        system_prompt = f"""你是一个资深的 B2B 外贸业务员。请根据买家询盘，结合【真实商品参数】，写一封极其专业的英文回信。
        ⚠️ 业务红线：1. 严格遵守阶梯价和起订量。2. 提取特征吸引客户。3. 结尾加入反问句。
        {context_str}"""

        with st.spinner("✍️ Action LLM 正在基于商业约束撰写高转化邮件..."):
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"买家询盘：\n{user_inquiry}"}
                ],
                temperature=temperature 
            )
            final_email = response.choices[0].message.content

        st.markdown("### ✉️ 最终商务邮件交付")
        st.info(final_email)

        # 演示用：闭环反馈展示
        st.markdown("---")
        st.write("📊 **RLHF 数据飞轮 (模拟)**")
        col_a, col_b, col_c = st.columns([1, 1, 2])
        if col_a.button("👍 发送并沉淀为优秀案例"):
            st.toast("✅ 数据已写入日志库，用于后续微调！", icon="📈")
        if col_b.button("👎 存在幻觉，标为 Bad Case"):
            st.toast("⚠️ 已上报算法团队排查！", icon="🚨")