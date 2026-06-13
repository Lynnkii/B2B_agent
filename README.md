# B2B_agent
# 🤖 B2B AI Sales Co-Pilot (跨境智能商机大模型引擎)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B)
![ChromaDB](https://img.shields.io/badge/VectorDB-Chroma-13C2C2)
![LLM](https://img.shields.io/badge/LLM-DeepSeek_V3-black)

## 📌 项目背景
针对传统跨境 B2B 电商面临的“跨语种长尾询盘响应慢、阶梯报价极易出错、纯 AI 容易产生价格幻觉”等痛点，本项目设计并开发了一套**基于企业级大语言模型架构的 B2B 人机协同智能工作台**。

## 🎯 核心业务特性
- **Intent Extraction (意图抽取降噪)**：使用冷温度 (T=0) 的 LLM 从冗长模糊的外贸邮件中精准提取核心品类。
- **Human-in-the-Loop (HITL 人机协同)**：引入人工确认阻断层，保障 B2B 商业场景 100% 的容错率。
- **Zero-Hallucination RAG (零幻觉检索增强)**：将真实的商品 SKU、MOQ (起订量) 与阶梯批发价作为强约束上下文，彻底杜绝 AI 乱报价。
- **MVC 架构解耦**：将底层高维向量算力层 (`brain.py`) 与 前端用户会话交互层 (`app.py`) 彻底剥离，具备千万级 SKU 扩展能力 (Scalability)。

## 🧠 技术架构
系统采用**双轨大模型协同 (Multi-Agent Routing)** 与**本地高维语义检索**：
1. **数据引擎**: 基于 `sentence-transformers` 对亚马逊真实商品数据进行 Embedding，灌入 `ChromaDB` 本地向量集群。
2. **检索大脑**: 抛弃传统字符串匹配，使用余弦相似度 (Cosine Similarity) 计算买家意图与底层商品的语义距离。
3. **交互前端**: 基于 `Streamlit` 构建现代化三栏式 Inbox SaaS 界面，搭载 RLHF 数据飞轮采集器。

## 🚀 极速启动 (Quick Start)
1. 配置环境：`pip install -r requirements.txt`
2. 根目录新建 `.env` 文件并填入：`DEEPSEEK_API_KEY=your_api_key_here`
3. 初始化向量数据库：`python build_vector_db.py`
4. 启动前端工作台：`streamlit run app.py`
