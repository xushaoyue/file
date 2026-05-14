import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from backend.app.config import settings, load_config


def main():
    config_path = os.environ.get("CONFIG_PATH")
    if config_path:
        loaded_settings = load_config(config_path)
    else:
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
