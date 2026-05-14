import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from backend.app.config import settings, load_config


def main():
    config_path = os.environ.get("CONFIG_PATH")
    
    if not config_path:
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_root = os.path.dirname(current_dir)
        config_path = os.path.join(project_root, "config", "config.yaml")
        print(f"未设置 CONFIG_PATH，使用默认路径: {config_path}")
    
    if os.path.exists(config_path):
        loaded_settings = load_config(config_path)
    else:
        print(f"配置文件不存在: {config_path}，使用默认配置")
        loaded_settings = settings

    uvicorn.run(
        "backend.app.main:app",
        host=loaded_settings.app.host,
        port=loaded_settings.app.port,
        reload=loaded_settings.app.debug,
        log_level=loaded_settings.log.level.lower()
    )


if __name__ == "__main__":
    main()
