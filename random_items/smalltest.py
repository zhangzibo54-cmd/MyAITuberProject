import torch

print(f"CUDA 是否可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA 版本: {torch.version.cuda}")
    print(f"GPU 名称: {torch.cuda.get_device_name(0)}")
else:
    print("PyTorch 无法找到 CUDA 设备。这是问题的核心。")