# My AITuber Project (我的AITuber项目)

这是一个结合了实时语音识别(STT)、大语言模型(LLM)、以及声音克隆(TTS)的AITuber项目。

## 架构简介 (Architecture)

本项目采用“云端+本地”的混合架构：
- **云端服务器 (大脑)**: 负责所有计算密集型任务，包括语音识别(Whisper/FunASR)、AI思考(Ollama)、以及声音合成(GPT-SoVITS)。
- **本地客户端 (身体与感官)**: 负责从用户的麦克风采集音频，并将云端返回的指令转化为声音播放和模型动作。

## 环境设置 (Setup Guide)

请按照以下步骤来配置和运行本项目。

### 1. 克隆本代码仓库
```bash
git clone [https://github.com/zhangzibo54-cmd/MyAITuberProject.git](https://github.com/zhangzibo54-cmd/MyAITuberProject.git)
cd MyAITuberProject
```
2. 下载AI模型文件 (重要)
本项目所需的AI模型文件体积较大，需要您手动下载并放置在指定的目录中。这些模型文件不应被上传到Git仓库。

GPT-SoVITS 模型:

请从您的训练来源下载 gpt.ckpt 和 sovits.pth 文件。

将它们分别放置在对应的角色文件夹中，例如：

KusanagiNene/gpt.ckpt

KusanagiNene/sovits.pth

XingTong/gpt.ckpt

XingTong/sovits.pth

声音参考音频:

请确保您的声音参考文件 (例如 ref.wav) 也已放置在对应的角色文件夹中。

Ollama 模型 (在云端服务器上执行):

本项目依赖 llama3 和 nomic-embed-text 模型。在您的云端服务器环境中，请运行以下命令进行下载：

```base
ollama pull llama3
ollama pull nomic-embed-text
```
---

### **第三部分：环境设置 (步骤3和4)**

markdown
### 3. 构建与部署云端服务器
本项目使用Docker进行环境打包和部署，以确保环境一致性。

1.  **构建Docker镜像** (在您本地电脑上):
    ```bash
    docker build -t your-dockerhub-username/aituber-server:v1 .
    ```
2.  **推送镜像到仓库**:
    ```bash
    docker push your-dockerhub-username/aituber-server:v1
    ```
3.  **在云端平台 (如RunPod) 部署**:
    * 租用一台合适的GPU服务器 (推荐RTX 3090/4090)。
    * 在部署时，使用您刚刚推送的Docker镜像名称。
    * 确保映射了您在`server.py`中使用的网络端口（例如8888）。

### 4. 运行本地客户端
在您的本地电脑上，配置好客户端程序（`local_client.py`）中的服务器地址，然后运行它以连接到云端大脑。

```bash
python local_client.py
```
