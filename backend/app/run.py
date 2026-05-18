import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 在导入 app 模块前设置 CONFIG_PATH，确保 settings 单例加载正确的配置文件
config_path = os.environ.get("CONFIG_PATH")
if not config_path:
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_root = os.path.dirname(current_dir)
    config_path = os.path.join(project_root, "config", "config.yaml")
    os.environ["CONFIG_PATH"] = config_path
    print(f"未设置 CONFIG_PATH，使用默认路径: {config_path}")

import uvicorn
from backend.app.config import settings


def main():
    if os.path.exists(config_path):
        print(f"已加载配置文件: {config_path}")
    else:
        print(f"配置文件不存在: {config_path}，使用默认配置")

    uvicorn.run(
        "backend.app.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
        log_level=settings.log.level.lower()
    )


if __name__ == "__main__":
    main()
