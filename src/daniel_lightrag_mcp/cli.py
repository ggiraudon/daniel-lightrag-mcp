"""
CLI entry point for the Daniel LightRAG MCP server.
"""

import argparse
import asyncio
import os
import sys
from .server import main, main_http


def cli():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Daniel LightRAG MCP Server",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default=os.getenv("MCP_TRANSPORT", "stdio"),
        help="Transport protocol (default: %(default)s, env: MCP_TRANSPORT)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_HOST", "0.0.0.0"),
        help="Host to bind (SSE transport only, default: %(default)s, env: MCP_HOST)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", "8000")),
        help="Port to bind (SSE transport only, default: %(default)s, env: MCP_PORT)",
    )

    args = parser.parse_args()

    try:
        if args.transport == "sse":
            asyncio.run(main_http(host=args.host, port=args.port))
        else:
            asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down server...")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
