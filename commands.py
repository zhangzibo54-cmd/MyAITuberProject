class Command:
    def __init__(self, command_type: str, data: any = None):
        self.type = command_type  # 命令类型, e.g., "CHAT", "STOP", "MEMORIZE"
        self.data = data          # 命令所需的数据
