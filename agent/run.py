import os

import uvicorn
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")


def main() -> None:
    host = os.environ.get("AGENT_HOST", "0.0.0.0")
    port = int(os.environ.get("AGENT_PORT", "5002"))
    uvicorn.run("app.server:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()
