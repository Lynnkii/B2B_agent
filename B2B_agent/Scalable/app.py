import streamlit as st
import pandas as pd
import brain  # 调用企业级解耦后台

# ==========================================
# 1. 网页 UI 全局设置 (宽屏展示模式)
# ==========================================
st.set_page_config(page_title="AI Sales Workspace", page_icon="💼", layout="wide")

# 尝试连接底层的向量数据库
try:
    collection = brain.get_vector_collection()
    db_status = True
    db_count = collection.count()
except Exception as e:
    db_status = False
    db_count = 0

# ==========================================
# 2. 状态管理 (Session State)
# ==========================================
if "current_step" not in st.session_state:
    st.session_state.current_step = 1
if "semantic_query" not in st.session_state:
    st.session_state.semantic_query = ""

# ==========================================
# 3. 侧边栏：面试“提词器”与全局设置
# ==========================================
with st.sidebar:
    st.image("https://img.alicdn.com/tfs/TB13DQPRFXXXXXGAPXXXXXXXXXX-330-94.png", width=150) # 阿里Logo
    st.markdown("### 👨‍💻 AI PM 核心架构看板")
    st.markdown("---")
    st.markdown("**🎯 解决核心痛点**\n- 跨语种长尾询盘响应慢\n- 业务员查阅阶梯价易出错\n- 纯AI极易产生“报价幻觉”")
    st.markdown("**🧠 架构演进 (Scalable)**\n- **基建**: ChromaDB 高维语义检索\n- **解耦**: 前后端 MVC 架构分离\n- **风控**: HITL 人机协同阻断\n- **行动**: RAG 强规则锚定生成")
    st.markdown("---")
    temperature = st.slider("🎛️ AI 创造力调节 (Temperature)", 0.0, 1.0, 0.2)
    
    if db_status:
        st.success(f"✅ 向量库在线 (SKU: {db_count})")
    else:
        st.error("🚨 数据库离线，请先执行灌库！")
        
    if st.button("🔄 重置演示状态", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

st.title("💼 B2B 智能接单 Agent ")
st.divider()

# ==========================================
# 4. 核心演示动线（双栏布局）
# ==========================================
col1, col2 = st.columns([1, 1.2], gap="large")

# ----------------- 左栏：商机录入与 HITL -----------------
with col1:
    st.subheader("📥 步骤 1：商机解析 (HITL)")
    
    # 【亮点】预设场景，一键切换演示
    scenarios = {
        "👗 场景 1：标准品类询盘 (测试语义匹配)": "Hi, I am an importer from Europe. I am looking for some fashion dresses for the upcoming summer season. I want to buy 300 pieces. Can you quote me the best price?",
        "🔌 场景 2：带特征要求的长尾询盘": "Hello, we are a retailer in Dubai. We need some fast charging cables or adapters. Quantity is around 400. Do you have anything with GaN technology? Send me CIF price.",
        "✍️ 场景 3：自定义手动输入": ""
    }
    selected_scenario = st.selectbox("⚡ 快速选择演示场景：", list(scenarios.keys()))
    
    # 当切换场景时，重置状态避免错乱
    if "last_scenario" not in st.session_state:
        st.session_state.last_scenario = selected_scenario
    if selected_scenario != st.session_state.last_scenario:
        st.session_state.current_step = 1
        st.session_state.semantic_query = ""
        st.session_state.last_scenario = selected_scenario
        st.rerun()

    user_inquiry = st.text_area("📨 海外买家原始询盘:", value=scenarios[selected_scenario], height=150)
    
    if st.session_state.current_step == 1:
        if st.button("🔍 1. 智能意图抽取 (Intent Extraction)", type="primary", use_container_width=True):
            if not user_inquiry.strip():
                st.warning("内容不能为空。")
                st.stop()
            with st.spinner("🧠 LLM 正在解析高维语义意图..."):
                # 调用解耦后台的方法
                st.session_state.semantic_query = brain.extract_intent(user_inquiry)
                st.session_state.current_step = 2
                st.rerun()

    if st.session_state.current_step >= 2:
        st.success("✨ AI 意图提取完成！已进入人机协同(HITL)确认环节。")
        final_query = st.text_input("✍️ 业务员确认/修改搜索语义 (防止AI抓错导致报价失误):", value=st.session_state.semantic_query)
        
        if st.button("🚀 2. 执行向量检索并渲染报价", type="primary", use_container_width=True):
            st.session_state.final_query = final_query
            st.session_state.current_step = 3
            st.rerun()

# ----------------- 右栏：向量召回与生成 -----------------
with col2:
    st.subheader("📤 步骤 2：防幻觉检索与生成")
    
    if st.session_state.current_step == 3:
        if not db_status:
            st.error("🚨 无法执行检索：底层向量库连接失败。")
            st.stop()

        search_failed = False
        with st.status(f"🌐 正在向量空间中计算语义余弦距离: '{st.session_state.final_query}'...", expanded=True) as status:
            # 执行向量检索
            results = collection.query(
                query_texts=[st.session_state.final_query],
                n_results=2
            )
            
            if not results['ids'][0]:
                status.update(label="未在向量库中匹配到有效数据", state="error", expanded=False)
                search_failed = True
            else:
                match_data = []
                for i in range(len(results['ids'][0])):
                    match_data.append({
                        "产品名称": results['metadatas'][0][i]['product_name'],
                        "底线规则 (MOQ/价格)": f"MOQ:{results['metadatas'][0][i]['moq']} | {results['metadatas'][0][i]['price_tier']}",
                        "语义距离": round(results['distances'][0][i], 4)
                    })
                st.write(f"✅ 成功命中！算法召回明细如下 (距离越小匹配度越高)：")
                st.dataframe(pd.DataFrame(match_data))
                status.update(label="RAG 向量召回成功", state="complete", expanded=False)

        if search_failed:
            st.error("⚠️ **风控拦截！**底库中无相关品类，请将此客户划拨至人工大客户团队。")
            st.stop() 

        # 调用解耦后台的方法渲染邮件
        with st.spinner("✍️ Action LLM 正在基于底层规则渲染商务邮件..."):
            final_email = brain.generate_quote_email(user_inquiry, results, temperature)

        st.markdown("### ✉️ 最终商务邮件交付")
        st.info(final_email)
        
        st.markdown("---")
        st.write("📊 **RLHF 数据反馈飞轮 (模拟)**")
        col_a, col_b, col_c = st.columns([1, 1, 2])
        if col_a.button("👍 发送并落库为优秀语料"):
            st.toast("✅ 数据已写入日志库，用于后续微调！", icon="📈")
        if col_b.button("👎 存在幻觉，标为 Bad Case"):
            st.toast("⚠️ 已上报算法团队排查！", icon="🚨")