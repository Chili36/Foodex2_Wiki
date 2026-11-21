"""Absolute-path entry point for MCP hosts that launch outside the repository."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wiki_mcp.server import main


if __name__ == "__main__":
    main()
