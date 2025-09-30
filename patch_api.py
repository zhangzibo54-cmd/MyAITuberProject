import sys
import os

# 目标文件是 api.py
API_PY_PATH = "/app/GPT-SoVITS/api.py"

# 定义绝对路径 (已根据我们发现的正确位置进行修正)
HUBERT_PATH = "/app/GPT-SoVITS/GPT_SoVITS/pretrained_models/chinese-hubert-base"
BERT_PATH = "/app/GPT-SoVITS/GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large"

print(f"--- 正在对 {API_PY_PATH} 执行超级修复 ---")

try:
    with open(API_PY_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    
    # 定义需要替换的规则
    replacements = {
        # 规则1 & 2: 硬编码路径 (Colab 方法)
        "cnhubert_base_path = args.hubert_path": f"cnhubert_base_path = '{HUBERT_PATH}'",
        "bert_path = args.bert_path": f"bert_path = '{BERT_PATH}'",
        
        # 规则3 & 4: 添加 local_files_only=True 作为安全网
        "AutoTokenizer.from_pretrained(bert_path)": "AutoTokenizer.from_pretrained(bert_path, local_files_only=True)",
        "AutoModelForMaskedLM.from_pretrained(bert_path)": "AutoModelForMaskedLM.from_pretrained(bert_path, local_files_only=True)"
    }

    # 执行所有替换
    for find_str, replace_str in replacements.items():
        if find_str in content:
            content = content.replace(find_str, replace_str)
            print(f"✅ 已应用规则: '{find_str}' -> '{replace_str[:50]}...'")
        else:
            print(f"⚠️ 未找到规则对应的代码: '{find_str}'")

    # 写回文件
    if content != original_content:
        with open(API_PY_PATH, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ 超级修复完成，api.py 已被修改。")
    else:
        print("🤷 文件无需修改或无法进行修改。")

except FileNotFoundError:
    print(f"❌ 错误：文件 '{API_PY_PATH}' 未找到。修补失败。")
    sys.exit(1)
except Exception as e:
    print(f"❌ 发生未知错误： {e}")
    sys.exit(1)