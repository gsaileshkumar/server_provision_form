import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

# Absolute path so the .env loads regardless of the shell's working directory.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)


def main() -> None:
    host = os.environ.get("AGENT_HOST", "0.0.0.0")
    port = int(os.environ.get("AGENT_PORT", "5002"))
    reload = os.environ.get("AGENT_RELOAD", "0") == "1"
    uvicorn.run("app.server:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
