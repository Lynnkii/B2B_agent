import pandas as pd
import random
import ssl

# 🔥 核心修复：强行绕过 macOS Python 默认的 SSL 证书验证拦截
ssl._create_default_https_context = ssl._create_unverified_context

print("🚀 正在通过 CDN 镜像加速节点，直连线上真实开源数据库...")

# 真实的开源电商数据集
online_db_url = "https://ghproxy.net/https://raw.githubusercontent.com/luminati-io/eCommerce-dataset-samples/main/shein-products.csv"

try:
    print(f"📥 正在发起 GET 请求拉取数据: {online_db_url}")
    # 直接拉取线上真实数据库
    df_raw = pd.read_csv(online_db_url)
    
    real_products = []
    print("✅ 成功连接真实数据库！正在提取 MVP 所需的前 20 条优质数据...")
    
    # 严格按照 MVP 原则，只取 20 条优质数据
    for index, row in df_raw.head(20).iterrows():
        
        retail_price = float(row['final_price'])
        
        # 商业降维：真实零售价 -> B2B 阶梯批发价
        price_tier_1 = round(retail_price * 0.6, 2)
        price_tier_2 = round(retail_price * 0.5, 2)
        price_tier_3 = round(retail_price * 0.4, 2)
        moq = random.choice([50, 100, 200])
        
        real_products.append({
            "sku_id": f"REAL-SKU-{index}",
            "product_name": str(row['product_name']).strip(),
            "category": "Cross-border E-commerce",
            "moq": moq,
            "price_tier": f"{moq}-{moq*4}: ${price_tier_1} | {moq*5}-{moq*9}: ${price_tier_2} | >={moq*10}: ${price_tier_3}",
            "core_features": str(row['description']).strip()[:300] + "..." 
        })

    df_mvp = pd.DataFrame(real_products)
    df_mvp.to_csv("/Users/lynn/Desktop/B2B_agent/MVP/products.csv", index=False, encoding='utf-8')
    
    print("🎯 MVP 数据集构建完成！打开左侧的 products.csv，你会看到 100% 来自线上的真实商品！")

except Exception as e:
    print(f"❌ 拉取失败，错误信息: {e}")