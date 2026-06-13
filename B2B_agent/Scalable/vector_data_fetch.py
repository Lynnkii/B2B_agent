import pandas as pd
import chromadb
import random
import ssl
import os

# 1. 强行绕过 macOS Python 默认的 SSL 证书拦截
ssl._create_default_https_context = ssl._create_unverified_context

# 2. 绝对路径锁定
current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir, "vector_db")
csv_path = os.path.join(current_dir, "products.csv")

print("🚀 [阶段 1] 正在直连线上获取真实数据源...")
online_db_url = "https://ghproxy.net/https://raw.githubusercontent.com/luminati-io/eCommerce-dataset-samples/main/shein-products.csv"

try:
    df_raw = pd.read_csv(online_db_url)
    real_products = []
    
    # 提取前 1000 条作为我们的高质生产数据源
    for index, row in df_raw.head(1000).iterrows():
        retail_price = float(row['final_price'])
        # 商业降维：生成阶梯价
        p1, p2, p3 = round(retail_price * 0.6, 2), round(retail_price * 0.5, 2), round(retail_price * 0.4, 2)
        moq = random.choice([50, 100, 200])
        
        real_products.append({
            "sku_id": f"SKU-PROD-{index}",
            "product_name": str(row['product_name']).strip(),
            "moq": moq,
            "price_tier": f"{moq}-{moq*4}: ${p1} | {moq*5}-{moq*9}: ${p2} | >={moq*10}: ${p3}",
            "core_features": str(row['description']).strip()[:400]
        })

    df = pd.DataFrame(real_products)
    df.to_csv(csv_path, index=False)
    print(f"✅ 数据清洗完成！共 {len(df)} 条商品。")

    print("🚀 [阶段 2] 正在初始化 ChromaDB 向量数据库并执行 Embedding 嵌入...")
    # 3. 初始化持久化向量数据库
    chroma_client = chromadb.PersistentClient(path=db_path)
    
    # 每次运行前清空旧库，保证数据最新
    try:
        chroma_client.delete_collection(name="b2b_products")
    except Exception:
        pass
        
    collection = chroma_client.create_collection(name="b2b_products")
    
    docs, metadatas, ids = [], [], []
    for idx, row in df.iterrows():
        # 将品名和特征合并，作为用于“被检索”的文本语义
        docs.append(f"{row['product_name']} - {row['core_features']}")
        # 将不可篡改的商业规则存入“元数据” (Metadata)
        metadatas.append({
            "product_name": row['product_name'],
            "moq": str(row['moq']),
            "price_tier": str(row['price_tier'])
        })
        ids.append(row['sku_id'])

    # 4. 执行向量化并写入数据库 (首次运行会自动下载 sentence-transformers 模型)
    collection.upsert(documents=docs, metadatas=metadatas, ids=ids)
    
    print(f"🎉 规模化灌库成功！向量数据库已持久化保存在: {db_path}")

except Exception as e:
    print(f"❌ 灌库失败: {e}")