#!/usr/bin/env python3
"""
Simple test script to verify the Greenhouse MCP server is working.
This tests that the server can be imported and initialized.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def test_import():
    """Test that we can import the MCP server."""
    try:
        from src.greenhouse_mcp import mcp  # noqa: F401

        print("✅ Successfully imported MCP server")
        return True
    except ImportError as e:
        print(f"❌ Failed to import MCP server: {e}")
        return False


def test_tools():
    """Test that tools are registered."""
    try:
        import asyncio

        from src.greenhouse_mcp import mcp

        tools = asyncio.run(mcp.list_tools())

        print(f"✅ Found {len(tools)} tools registered:")

        expected_tools = [
            # Jobs
            "list_jobs",
            "get_job",
            "create_job",
            "update_job",
            "list_job_posts_for_job",
            # Candidates
            "list_candidates",
            "get_candidate",
            "create_candidate",
            "update_candidate",
            "add_note_to_candidate",
            # Applications
            "list_applications",
            "get_application",
            "advance_application",
            "reject_application",
            "add_note_to_application",
            # Job openings + close reasons
            "list_job_openings",
            "get_job_opening",
            "create_job_openings",
            "update_job_opening",
            "close_job_opening",
            "reopen_job_opening",
            "delete_job_opening",
            "list_close_reasons",
            # Job stages
            "list_job_stages",
            "list_job_stages_for_job",
            "get_job_stage",
            # Hiring team
            "get_job_hiring_team",
            "add_hiring_team_members",
            "replace_hiring_team",
            "remove_hiring_team_member",
            # Org data
            "list_departments",
            "list_offices",
            "list_users",
        ]

        tool_names = [
            tool.name if hasattr(tool, "name") else str(tool) for tool in tools
        ]

        for name in sorted(tool_names):
            print(f"   - {name}")

        missing_tools = [t for t in expected_tools if t not in tool_names]

        if missing_tools:
            print(f"⚠️  Missing expected tools: {missing_tools}")
            return False

        return True
    except Exception as e:
        print(f"❌ Failed to list tools: {e}")
        return False


def test_env_check():
    """Test environment variable configuration."""
    api_key = os.getenv("GREENHOUSE_API_KEY")

    if api_key:
        print(f"✅ GREENHOUSE_API_KEY is set (length: {len(api_key)} chars)")
        return True
    else:
        print("⚠️  GREENHOUSE_API_KEY is not set")
        print("   Set it in .env file or environment to use the server")
        return None  # Warning, not failure


def main():
    """Run all tests."""
    print("Testing Greenhouse MCP Server...\n")

    results = []

    # Test imports
    results.append(test_import())

    # Test tools
    if results[-1]:  # Only test tools if import succeeded
        results.append(test_tools())

    # Test environment
    env_result = test_env_check()
    if env_result is not None:
        results.append(env_result)

    print("\n" + "=" * 50)

    if all(results):
        print("✅ All tests passed! Server is ready to use.")
        print("\nTo run the server:")
        print("  fastmcp run src.greenhouse_mcp:mcp")
        print("\nOr with Python:")
        print("  python -m src.greenhouse_mcp")
        return 0
    elif any(r is False for r in results):
        print("❌ Some tests failed. Please check the errors above.")
        return 1
    else:
        print("⚠️  Server is functional but needs configuration.")
        print("Please set GREENHOUSE_API_KEY in your .env file.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
