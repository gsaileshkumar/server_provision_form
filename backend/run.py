from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")

from app import create_app
from app.config import Config


def main() -> None:
    app = create_app()
    app.run(host=Config.host, port=Config.port, debug=True)


if __name__ == "__main__":
    main()
