import requests
import json
import os
import sys

# --- 1. 自动获取 Runpod 地址 ---
# 这是一个辅助函数，用于获取用户输入的IP和端口
def get_runpod_url():
    print("=================================================")
    print("  GPT-SoVITS API 远程测试工具 (Python)")
    print("=================================================")

    # 🚨 警告：如果您不替换成您的实际地址，程序会崩溃！
    default_ip = "194.68.245.153"
    default_port = "22003" 


    public_ip =  default_ip
    mapped_port =  default_port

    return f"http://{public_ip}:{mapped_port}/"

# --- 2. 定义 TTS 请求参数 ---
def get_payload():
    # ⚠️ 这些参数必须与您在启动命令中使用的参数一致 ⚠️
    return {
        "refer_wav_path": "/app/XingTong/ref.wav",
        "prompt_text": "等你，我想想，嗯。",
        "prompt_language": "zh",
        "text": "你在干什么。",
        "text_language": "zh",
        # 优化推理参数，如果您需要调整
        "top_k": 20,
        "top_p": 0.8,
        "temperature": 0.8,
        "speed": 1
    }

# --- 3. 执行请求和保存文件 ---
def run_test():
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            # 强制将标准输出的编码设置为 UTF-8，以支持表情符号和中文
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            # 如果 reconfigure 不可用（例如某些旧环境），则继续，但可能会显示乱码
            pass
    # ==========================

    api_url = get_runpod_url()
    payload = get_payload()
    output_filename = "synthesized_tts_output.wav"

    print("\n--- 正在准备发送请求 ---")
    print(f"API URL: {api_url}")
    print(f"合成文本: {payload['text']}")
    print(f"目标文件: {output_filename}")
    print("-------------------------")

    try:
        # 发送 POST 请求，timeout 设置长一点以应对模型推理时间
        response = requests.post(api_url, json=payload, timeout=180)

        # 检查响应
        if response.status_code == 200 and 'audio' in response.headers.get('Content-Type', ''):
            audio_data = response.content
            
            # 将音频数据写入本地文件
            with open(output_filename, "wb") as f:
                f.write(audio_data)
            
            file_size_kb = os.path.getsize(output_filename) / 1024
            
            print(f"\n✅ 请求成功！音频已下载并保存至 {output_filename}")
            print(f"   文件大小: {file_size_kb:.2f} KB。")
            
        else:
            print(f"\n❌ 请求失败！服务器返回了错误信息。")
            print(f"  - 状态码: {response.status_code}")
            # 尝试解析 JSON 错误详情
            try:
                error_details = response.json()
                print(f"  - 错误详情: {json.dumps(error_details, indent=4, ensure_ascii=False)}")
            except json.JSONDecodeError:
                print(f"  - 原始响应文本: {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("\n❌ 连接错误：无法连接到服务器。")
        print("   请检查您的 IP 和端口是否正确，并确保 Runpod 上的 Pod 正在运行且端口已暴露。")
    except Exception as e:
        print(f"\n❌ 请求过程中发生意外错误: {e}")
        
if __name__ == "__main__":
    try:
        run_test()
    except KeyboardInterrupt:
        print("\n测试程序已中断。")
        sys.exit(0)