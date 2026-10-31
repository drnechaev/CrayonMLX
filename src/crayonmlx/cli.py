"""Local-only application entry point."""

import argparse

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="CrayonMLX — локальная студия для рисунков")
    parser.add_argument("--port", type=int, default=8787)
    arguments = parser.parse_args()
    uvicorn.run("crayonmlx.app:create_app", factory=True, host="127.0.0.1", port=arguments.port)
