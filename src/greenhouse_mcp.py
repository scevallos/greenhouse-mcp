#!/usr/bin/env python3
import os
import json
from typing import Optional, List, Dict, Any
from fastmcp import FastMCP, Context
from dotenv import load_dotenv

from .greenhouse_client import GreenhouseClient
from .models import (
    Job, Candidate, Application, Note,
    CandidateCreateRequest, ApplicationAdvanceRequest
)

load_dotenv()

mcp = FastMCP("Greenhouse API 🌱")
mcp.description = "MCP server for interacting with Greenhouse Harvest API"

client: Optional[GreenhouseClient] = None


def get_client() -> GreenhouseClient:
    global client
    if client is None:
        api_key = os.getenv("GREENHOUSE_API_KEY")
        if not api_key:
            raise ValueError(
                "GREENHOUSE_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )
        client = GreenhouseClient(api_key)
    return client


@mcp.tool
async def list_jobs(
    per_page: int = 50,
    page: int = 1,
    status: Optional[str] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    auto_paginate: bool = False,
    ctx: Context = None
) -> List[Dict[str, Any]]:
    """
    List all jobs in Greenhouse.

    Args:
        per_page: Number of results per page (max 500)
        page: Page number to retrieve
        status: Filter by job status (open, closed, draft)
        created_after: ISO 8601 date to filter jobs created after
        created_before: ISO 8601 date to filter jobs created before
        auto_paginate: If true, follow Link headers to fetch all pages

    Returns:
        List of job objects
    """
    try:
        gh_client = get_client()
        jobs = await gh_client.list_jobs(
            per_page=per_page,
            page=page,
            status=status,
            created_after=created_after,
            created_before=created_before,
            auto_paginate=auto_paginate,
        )
        if ctx:
            ctx.info(f"Retrieved {len(jobs)} jobs")
        return jobs
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to list jobs: {str(e)}")
        raise


@mcp.tool
async def get_job(
    job_id: int,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific job.

    Args:
        job_id: The ID of the job to retrieve

    Returns:
        Job object with full details
    """
    try:
        gh_client = get_client()
        job = await gh_client.get_job(job_id)
        if ctx:
            ctx.info(f"Retrieved job: {job.get('name', 'Unknown')}")
        return job
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to get job {job_id}: {str(e)}")
        raise


@mcp.tool
async def list_candidates(
    per_page: int = 50,
    page: int = 1,
    email: Optional[str] = None,
    candidate_ids: Optional[List[int]] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    auto_paginate: bool = False,
    ctx: Context = None
) -> List[Dict[str, Any]]:
    """
    List candidates in Greenhouse.

    Args:
        per_page: Number of results per page (max 500)
        page: Page number to retrieve
        email: Filter by candidate email address
        candidate_ids: List of specific candidate IDs to retrieve
        created_after: ISO 8601 date to filter candidates created after
        created_before: ISO 8601 date to filter candidates created before
        auto_paginate: If true, follow Link headers to fetch all pages

    Returns:
        List of candidate objects
    """
    try:
        gh_client = get_client()
        candidates = await gh_client.list_candidates(
            per_page=per_page,
            page=page,
            email=email,
            candidate_ids=candidate_ids,
            created_after=created_after,
            created_before=created_before,
            auto_paginate=auto_paginate,
        )
        if ctx:
            ctx.info(f"Retrieved {len(candidates)} candidates")
        return candidates
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to list candidates: {str(e)}")
        raise


@mcp.tool
async def get_candidate(
    candidate_id: int,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific candidate.

    Args:
        candidate_id: The ID of the candidate to retrieve

    Returns:
        Candidate object with full details
    """
    try:
        gh_client = get_client()
        candidate = await gh_client.get_candidate(candidate_id)
        if ctx:
            name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}"
            ctx.info(f"Retrieved candidate: {name.strip() or 'Unknown'}")
        return candidate
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to get candidate {candidate_id}: {str(e)}")
        raise


@mcp.tool
async def create_candidate(
    first_name: str,
    last_name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    title: Optional[str] = None,
    tags: Optional[List[str]] = None,
    on_behalf_of: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Create a new candidate in Greenhouse.

    Args:
        first_name: Candidate's first name
        last_name: Candidate's last name
        email: Candidate's email address
        phone: Candidate's phone number
        company: Current company
        title: Current job title
        tags: List of tags to apply to the candidate
        on_behalf_of: Greenhouse user ID to attribute the action to.
            Falls back to GREENHOUSE_USER_ID env var.

    Returns:
        Created candidate object
    """
    try:
        gh_client = get_client()

        candidate_data: Dict[str, Any] = {
            "first_name": first_name,
            "last_name": last_name,
        }

        if email:
            candidate_data["email_addresses"] = [
                {"value": email, "type": "personal"}
            ]

        if phone:
            candidate_data["phone_numbers"] = [
                {"value": phone, "type": "mobile"}
            ]

        if company:
            candidate_data["company"] = company

        if title:
            candidate_data["title"] = title

        if tags:
            candidate_data["tags"] = tags

        candidate = await gh_client.create_candidate(
            candidate_data, on_behalf_of=on_behalf_of
        )

        if ctx:
            ctx.info(f"Created candidate: {first_name} {last_name}")

        return candidate
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to create candidate: {str(e)}")
        raise


@mcp.tool
async def update_candidate(
    candidate_id: int,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    title: Optional[str] = None,
    tags: Optional[List[str]] = None,
    on_behalf_of: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Update an existing candidate in Greenhouse.

    Args:
        candidate_id: ID of the candidate to update
        first_name: Updated first name
        last_name: Updated last name
        email: Updated email address
        phone: Updated phone number
        company: Updated company
        title: Updated job title
        tags: Updated list of tags
        on_behalf_of: Greenhouse user ID to attribute the action to.
            Falls back to GREENHOUSE_USER_ID env var.

    Returns:
        Updated candidate object
    """
    try:
        gh_client = get_client()

        update_data: Dict[str, Any] = {}

        if first_name:
            update_data["first_name"] = first_name

        if last_name:
            update_data["last_name"] = last_name

        if email:
            update_data["email_addresses"] = [
                {"value": email, "type": "personal"}
            ]

        if phone:
            update_data["phone_numbers"] = [
                {"value": phone, "type": "mobile"}
            ]

        if company:
            update_data["company"] = company

        if title:
            update_data["title"] = title

        if tags:
            update_data["tags"] = tags

        candidate = await gh_client.update_candidate(
            candidate_id, update_data, on_behalf_of=on_behalf_of
        )

        if ctx:
            ctx.info(f"Updated candidate ID: {candidate_id}")

        return candidate
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to update candidate {candidate_id}: {str(e)}")
        raise


@mcp.tool
async def list_applications(
    per_page: int = 50,
    page: int = 1,
    job_id: Optional[int] = None,
    candidate_id: Optional[int] = None,
    status: Optional[str] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    auto_paginate: bool = False,
    ctx: Context = None
) -> List[Dict[str, Any]]:
    """
    List applications in Greenhouse.

    Args:
        per_page: Number of results per page (max 500)
        page: Page number to retrieve
        job_id: Filter by job ID
        candidate_id: Filter by candidate ID
        status: Filter by application status
        created_after: ISO 8601 date to filter applications created after
        created_before: ISO 8601 date to filter applications created before
        auto_paginate: If true, follow Link headers to fetch all pages

    Returns:
        List of application objects
    """
    try:
        gh_client = get_client()
        applications = await gh_client.list_applications(
            per_page=per_page,
            page=page,
            job_id=job_id,
            candidate_id=candidate_id,
            status=status,
            created_after=created_after,
            created_before=created_before,
            auto_paginate=auto_paginate,
        )
        if ctx:
            ctx.info(f"Retrieved {len(applications)} applications")
        return applications
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to list applications: {str(e)}")
        raise


@mcp.tool
async def get_application(
    application_id: int,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific application.

    Args:
        application_id: The ID of the application to retrieve

    Returns:
        Application object with full details
    """
    try:
        gh_client = get_client()
        application = await gh_client.get_application(application_id)
        if ctx:
            ctx.info(f"Retrieved application ID: {application_id}")
        return application
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to get application {application_id}: {str(e)}")
        raise


@mcp.tool
async def advance_application(
    application_id: int,
    from_stage_id: int,
    to_stage_id: Optional[int] = None,
    on_behalf_of: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Advance an application to the next stage in the hiring process.

    Args:
        application_id: ID of the application to advance
        from_stage_id: Current stage ID (must match the application's current stage)
        to_stage_id: Target stage ID (if not provided, advances to next stage)
        on_behalf_of: Greenhouse user ID to attribute the action to.
            Falls back to GREENHOUSE_USER_ID env var.

    Returns:
        Success confirmation
    """
    try:
        gh_client = get_client()
        result = await gh_client.advance_application(
            application_id=application_id,
            from_stage_id=from_stage_id,
            to_stage_id=to_stage_id,
            on_behalf_of=on_behalf_of,
        )
        if ctx:
            ctx.info(f"Advanced application {application_id}")
        return result
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to advance application {application_id}: {str(e)}")
        raise


@mcp.tool
async def reject_application(
    application_id: int,
    rejection_reason_id: Optional[int] = None,
    notes: Optional[str] = None,
    on_behalf_of: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Reject an application.

    Args:
        application_id: ID of the application to reject
        rejection_reason_id: ID of the rejection reason (optional)
        notes: Additional notes about the rejection (optional)
        on_behalf_of: Greenhouse user ID to attribute the action to.
            Falls back to GREENHOUSE_USER_ID env var.

    Returns:
        Success confirmation
    """
    try:
        gh_client = get_client()
        result = await gh_client.reject_application(
            application_id=application_id,
            rejection_reason_id=rejection_reason_id,
            notes=notes,
            on_behalf_of=on_behalf_of,
        )
        if ctx:
            ctx.info(f"Rejected application {application_id}")
        return result
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to reject application {application_id}: {str(e)}")
        raise


@mcp.tool
async def add_note_to_candidate(
    candidate_id: int,
    note: str,
    visibility: str = "private",
    on_behalf_of: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Add a note to a candidate's activity feed.

    Args:
        candidate_id: ID of the candidate
        note: The note content
        visibility: Note visibility (admin_only, private, or public)
        on_behalf_of: Greenhouse user ID to attribute the action to.
            Falls back to GREENHOUSE_USER_ID env var.

    Returns:
        Created note object
    """
    try:
        gh_client = get_client()
        result = await gh_client.add_note_to_candidate(
            candidate_id=candidate_id,
            body=note,
            visibility=visibility,
            on_behalf_of=on_behalf_of,
        )
        if ctx:
            ctx.info(f"Added note to candidate {candidate_id}")
        return result
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to add note to candidate {candidate_id}: {str(e)}")
        raise


@mcp.tool
async def add_note_to_application(
    application_id: int,
    note: str,
    visibility: str = "private",
    on_behalf_of: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Add a note to an application.

    Args:
        application_id: ID of the application
        note: The note content
        visibility: Note visibility (admin_only, private, or public)
        on_behalf_of: Greenhouse user ID to attribute the action to.
            Falls back to GREENHOUSE_USER_ID env var.

    Returns:
        Created note object
    """
    try:
        gh_client = get_client()
        result = await gh_client.add_note_to_application(
            application_id=application_id,
            body=note,
            visibility=visibility,
            on_behalf_of=on_behalf_of,
        )
        if ctx:
            ctx.info(f"Added note to application {application_id}")
        return result
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to add note to application {application_id}: {str(e)}")
        raise


@mcp.tool
async def list_departments(
    per_page: int = 50,
    page: int = 1,
    auto_paginate: bool = False,
    ctx: Context = None
) -> List[Dict[str, Any]]:
    """
    List all departments in Greenhouse.

    Args:
        per_page: Number of results per page
        page: Page number to retrieve
        auto_paginate: If true, follow Link headers to fetch all pages

    Returns:
        List of department objects
    """
    try:
        gh_client = get_client()
        departments = await gh_client.list_departments(
            per_page=per_page,
            page=page,
            auto_paginate=auto_paginate,
        )
        if ctx:
            ctx.info(f"Retrieved {len(departments)} departments")
        return departments
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to list departments: {str(e)}")
        raise


@mcp.tool
async def list_offices(
    per_page: int = 50,
    page: int = 1,
    auto_paginate: bool = False,
    ctx: Context = None
) -> List[Dict[str, Any]]:
    """
    List all offices in Greenhouse.

    Args:
        per_page: Number of results per page
        page: Page number to retrieve
        auto_paginate: If true, follow Link headers to fetch all pages

    Returns:
        List of office objects
    """
    try:
        gh_client = get_client()
        offices = await gh_client.list_offices(
            per_page=per_page,
            page=page,
            auto_paginate=auto_paginate,
        )
        if ctx:
            ctx.info(f"Retrieved {len(offices)} offices")
        return offices
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to list offices: {str(e)}")
        raise


@mcp.tool
async def list_users(
    per_page: int = 50,
    page: int = 1,
    email: Optional[str] = None,
    auto_paginate: bool = False,
    ctx: Context = None
) -> List[Dict[str, Any]]:
    """
    List users in Greenhouse.

    Args:
        per_page: Number of results per page
        page: Page number to retrieve
        email: Filter by user email address
        auto_paginate: If true, follow Link headers to fetch all pages

    Returns:
        List of user objects
    """
    try:
        gh_client = get_client()
        users = await gh_client.list_users(
            per_page=per_page,
            page=page,
            email=email,
            auto_paginate=auto_paginate,
        )
        if ctx:
            ctx.info(f"Retrieved {len(users)} users")
        return users
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to list users: {str(e)}")
        raise


def main():
    """Main entry point for the MCP server."""
    import sys

    if not os.getenv("GREENHOUSE_API_KEY"):
        print("Error: GREENHOUSE_API_KEY environment variable is required", file=sys.stderr)
        print("Please set it in your .env file or environment.", file=sys.stderr)
        sys.exit(1)

    mcp.run()


if __name__ == "__main__":
    main()
