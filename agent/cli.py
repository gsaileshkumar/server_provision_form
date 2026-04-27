"""Tiny REPL for chatting with the server provisioning agent."""

from __future__ import annotations

import sys

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

from agent import build_agent


def main() -> int:
    load_dotenv()
    agent = build_agent()
    history: list = []

    print("Server provisioning agent. Type 'exit' to quit.\n")
    while True:
        try:
            user = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not user:
            continue
        if user.lower() in {"exit", "quit"}:
            return 0

        history.append(HumanMessage(content=user))
        result = agent.invoke({"messages": history})
        history = result["messages"]
        last = history[-1]
        if isinstance(last, AIMessage):
            print(f"agent> {last.content}\n")
        else:
            print(f"agent> {getattr(last, 'content', last)}\n")


if __name__ == "__main__":
    sys.exit(main())
