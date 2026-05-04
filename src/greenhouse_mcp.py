#!/usr/bin/env python3
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastmcp import Context, FastMCP

from .greenhouse_client import GreenhouseClient

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
    ctx: Context = None,
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
async def get_job(job_id: int, ctx: Context = None) -> Dict[str, Any]:
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
async def create_job(
    template_job_id: int,
    job_name: Optional[str] = None,
    job_post_name: Optional[str] = None,
    number_of_openings: Optional[int] = None,
    department_id: Optional[int] = None,
    office_ids: Optional[List[int]] = None,
    requisition_id: Optional[str] = None,
    opening_ids: Optional[List[str]] = None,
    on_behalf_of: Optional[str] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Create a new job by cloning an existing template job.

    Greenhouse requires a template_job_id — jobs are always created by copying
    an existing job's interview plan, scorecard, and settings. To find a
    template, look at list_jobs (any existing job can serve as a template).

    Args:
        template_job_id: ID of an existing job to clone settings from
        job_name: Name for the new job (defaults to the template's name)
        job_post_name: Name for the public-facing job post
        number_of_openings: How many openings to create on the new job
        department_id: Department to assign the new job to
        office_ids: Office IDs to assign the new job to
        requisition_id: Custom requisition ID string for the new job
        opening_ids: Human-readable opening IDs (e.g. ["REQ-1234"]) — if
            provided, length should match number_of_openings
        on_behalf_of: Greenhouse user ID to attribute the action to.
            Falls back to GREENHOUSE_USER_ID env var.

    Returns:
        Created job object
    """
    try:
        data: Dict[str, Any] = {"template_job_id": template_job_id}
        if job_name is not None:
            data["job_name"] = job_name
        if job_post_name is not None:
            data["job_post_name"] = job_post_name
        if number_of_openings is not None:
            data["number_of_openings"] = number_of_openings
        if department_id is not None:
            data["department_id"] = department_id
        if office_ids is not None:
            data["office_ids"] = office_ids
        if requisition_id is not None:
            data["requisition_id"] = requisition_id
        if opening_ids is not None:
            data["opening_ids"] = opening_ids

        gh_client = get_client()
        job = await gh_client.create_job(data, on_behalf_of=on_behalf_of)
        if ctx:
            ctx.info(f"Created job: {job.get('name', job_name or 'Unknown')}")
        return job
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to create job: {str(e)}")
        raise


@mcp.tool
async def update_job(
    job_id: int,
    name: Optional[str] = None,
    notes: Optional[str] = None,
    requisition_id: Optional[str] = None,
    team_id: Optional[int] = None,
    department_id: Optional[int] = None,
    office_ids: Optional[List[int]] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
    on_behalf_of: Optional[str] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Update an existing job's metadata — rename, move to a different
    department or office, change requisition ID, or update custom fields.

    Note: this does not change job status. To close a job, close each of its
    openings via close_job_opening (or update_job_opening).

    Args:
        job_id: ID of the job to update
        name: New name for the job
        notes: Updated job notes
        requisition_id: Updated custom requisition ID
        team_id: Team ID to assign the job to
        department_id: Department ID to move the job to
        office_ids: New full list of office IDs (replaces existing)
        custom_fields: Custom field values to set
        on_behalf_of: Greenhouse user ID to attribute the action to.
            Falls back to GREENHOUSE_USER_ID env var.

    Returns:
        Updated job object
    """
    try:
        data: Dict[str, Any] = {}
        if name is not None:
            data["name"] = name
        if notes is not None:
            data["notes"] = notes
        if requisition_id is not None:
            data["requisition_id"] = requisition_id
        if team_id is not None:
            data["team_id"] = team_id
        if department_id is not None:
            data["department_id"] = department_id
        if office_ids is not None:
            data["office_ids"] = office_ids
        if custom_fields is not None:
            data["custom_fields"] = custom_fields

        if not data:
            raise ValueError(
                "update_job requires at least one of name, notes, "
                "requisition_id, team_id, department_id, office_ids, "
                "or custom_fields"
            )

        gh_client = get_client()
        job = await gh_client.update_job(job_id, data, on_behalf_of=on_behalf_of)
        if ctx:
            ctx.info(f"Updated job {job_id}")
        return job
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to update job {job_id}: {str(e)}")
        raise


@mcp.tool
async def list_job_posts_for_job(
    job_id: int,
    per_page: int = 50,
    page: int = 1,
    active: Optional[bool] = None,
    live: Optional[bool] = None,
    full_content: Optional[bool] = None,
    auto_paginate: bool = False,
    ctx: Context = None,
) -> List[Dict[str, Any]]:
    """
    List the public-facing job posts attached to a job.

    A job can have multiple posts (e.g. one per office, or different
    audiences). Each post has its own title, location, content, and
    application questions.

    Args:
        job_id: ID of the job
        per_page: Results per page
        page: Page number
        active: If true, only return active posts
        live: If true, only return posts currently live on the job board
        full_content: If true, include the full post body and questions
        auto_paginate: If true, follow Link headers to fetch all pages

    Returns:
        List of job post objects
    """
    try:
        gh_client = get_client()
        posts = await gh_client.list_job_posts_for_job(
            job_id,
            per_page=per_page,
            page=page,
            active=active,
            live=live,
            full_content=full_content,
            auto_paginate=auto_paginate,
        )
        if ctx:
            ctx.info(f"Retrieved {len(posts)} job posts for job {job_id}")
        return posts
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to list job posts for job {job_id}: {str(e)}")
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
    ctx: Context = None,
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
async def get_candidate(candidate_id: int, ctx: Context = None) -> Dict[str, Any]:
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
    ctx: Context = None,
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
            candidate_data["email_addresses"] = [{"value": email, "type": "personal"}]

        if phone:
            candidate_data["phone_numbers"] = [{"value": phone, "type": "mobile"}]

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
    ctx: Context = None,
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
            update_data["email_addresses"] = [{"value": email, "type": "personal"}]

        if phone:
            update_data["phone_numbers"] = [{"value": phone, "type": "mobile"}]

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
    ctx: Context = None,
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
async def get_application(application_id: int, ctx: Context = None) -> Dict[str, Any]:
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
    ctx: Context = None,
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
    ctx: Context = None,
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
    ctx: Context = None,
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
    ctx: Context = None,
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
    per_page: int = 50, page: int = 1, auto_paginate: bool = False, ctx: Context = None
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
    per_page: int = 50, page: int = 1, auto_paginate: bool = False, ctx: Context = None
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
    ctx: Context = None,
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


@mcp.tool
async def list_job_openings(
    per_page: int = 50,
    page: int = 1,
    status: Optional[str] = None,
    opening_id: Optional[str] = None,
    skip_count: Optional[bool] = None,
    auto_paginate: bool = False,
    ctx: Context = None,
) -> List[Dict[str, Any]]:
    """
    List job openings across the organization.

    A job opening is a discrete headcount slot under a job. One job can have
    many openings, each with its own status (open, closed), close_reason,
    and custom fields.

    Args:
        per_page: Results per page (max 500)
        page: Page number
        status: Filter by status (open, closed)
        opening_id: Filter by the human-readable opening ID
        skip_count: If true, skips the total-count query for faster responses
        auto_paginate: If true, follow Link headers to fetch all pages

    Returns:
        List of job opening objects
    """
    try:
        gh_client = get_client()
        openings = await gh_client.list_job_openings(
            per_page=per_page,
            page=page,
            status=status,
            opening_id=opening_id,
            skip_count=skip_count,
            auto_paginate=auto_paginate,
        )
        if ctx:
            ctx.info(f"Retrieved {len(openings)} job openings")
        return openings
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to list job openings: {str(e)}")
        raise


@mcp.tool
async def get_job_opening(
    job_id: int, opening_id: int, ctx: Context = None
) -> Dict[str, Any]:
    """
    Retrieve a single opening for a specific job.

    Args:
        job_id: ID of the parent job
        opening_id: Numeric ID of the opening

    Returns:
        Job opening object
    """
    try:
        gh_client = get_client()
        opening = await gh_client.get_job_opening(job_id, opening_id)
        if ctx:
            ctx.info(f"Retrieved opening {opening_id} for job {job_id}")
        return opening
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to get opening {opening_id}: {str(e)}")
        raise


@mcp.tool
async def create_job_openings(
    job_id: int,
    quantity: int = 1,
    opening_ids: Optional[List[str]] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
    on_behalf_of: Optional[str] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Create one or more job openings under a job.

    Args:
        job_id: ID of the job to add openings to
        quantity: Number of openings to create (used when opening_ids is not given)
        opening_ids: Optional list of human-readable opening IDs (e.g. ["REQ-1234"]).
            If provided, length determines how many openings are created.
        custom_fields: Custom field values to apply to every new opening
        on_behalf_of: Greenhouse user ID to attribute the action to.
            Falls back to GREENHOUSE_USER_ID env var.

    Returns:
        Greenhouse response containing the created openings
    """
    try:
        gh_client = get_client()

        if opening_ids:
            openings = [{"opening_id": oid} for oid in opening_ids]
        else:
            openings = [{} for _ in range(quantity)]

        if custom_fields:
            for opening in openings:
                opening["custom_fields"] = custom_fields

        result = await gh_client.create_job_openings(
            job_id, openings, on_behalf_of=on_behalf_of
        )
        if ctx:
            ctx.info(f"Created {len(openings)} opening(s) on job {job_id}")
        return result
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to create openings on job {job_id}: {str(e)}")
        raise


@mcp.tool
async def update_job_opening(
    opening_id: int,
    status: Optional[str] = None,
    close_reason_id: Optional[int] = None,
    application_id: Optional[int] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
    on_behalf_of: Optional[str] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Update a job opening — change status, close reason, linked application,
    or custom fields.

    For the common cases of closing or reopening, prefer close_job_opening
    and reopen_job_opening which set the right fields automatically.

    Args:
        opening_id: Numeric ID of the opening to update
        status: New status ("open" or "closed")
        close_reason_id: Close reason (required when closing for non-hire reasons;
            see list_close_reasons for valid IDs)
        application_id: Application ID to link the opening to (e.g. when hiring)
        custom_fields: Custom field values to set
        on_behalf_of: Greenhouse user ID to attribute the action to.
            Falls back to GREENHOUSE_USER_ID env var.

    Returns:
        Updated opening object
    """
    try:
        data: Dict[str, Any] = {}
        if status:
            data["status"] = status
        if close_reason_id is not None:
            data["close_reason_id"] = close_reason_id
        if application_id is not None:
            data["application_id"] = application_id
        if custom_fields:
            data["custom_fields"] = custom_fields

        if not data:
            raise ValueError(
                "update_job_opening requires at least one of status, "
                "close_reason_id, application_id, or custom_fields"
            )

        gh_client = get_client()
        result = await gh_client.update_job_opening(
            opening_id, data, on_behalf_of=on_behalf_of
        )
        if ctx:
            ctx.info(f"Updated opening {opening_id}")
        return result
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to update opening {opening_id}: {str(e)}")
        raise


@mcp.tool
async def close_job_opening(
    opening_id: int,
    close_reason_id: Optional[int] = None,
    on_behalf_of: Optional[str] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Close a job opening. Convenience wrapper around update_job_opening.

    Args:
        opening_id: Numeric ID of the opening to close
        close_reason_id: ID of the close reason (see list_close_reasons).
            Required by Greenhouse for closures other than "hired".
        on_behalf_of: Greenhouse user ID to attribute the action to.
            Falls back to GREENHOUSE_USER_ID env var.

    Returns:
        Updated opening object
    """
    try:
        data: Dict[str, Any] = {"status": "closed"}
        if close_reason_id is not None:
            data["close_reason_id"] = close_reason_id

        gh_client = get_client()
        result = await gh_client.update_job_opening(
            opening_id, data, on_behalf_of=on_behalf_of
        )
        if ctx:
            ctx.info(f"Closed opening {opening_id}")
        return result
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to close opening {opening_id}: {str(e)}")
        raise


@mcp.tool
async def reopen_job_opening(
    opening_id: int, on_behalf_of: Optional[str] = None, ctx: Context = None
) -> Dict[str, Any]:
    """
    Reopen a previously closed job opening.

    Args:
        opening_id: Numeric ID of the opening to reopen
        on_behalf_of: Greenhouse user ID to attribute the action to.
            Falls back to GREENHOUSE_USER_ID env var.

    Returns:
        Updated opening object
    """
    try:
        gh_client = get_client()
        result = await gh_client.update_job_opening(
            opening_id, {"status": "open"}, on_behalf_of=on_behalf_of
        )
        if ctx:
            ctx.info(f"Reopened opening {opening_id}")
        return result
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to reopen opening {opening_id}: {str(e)}")
        raise


@mcp.tool
async def delete_job_opening(
    opening_id: int,
    confirm: bool = False,
    on_behalf_of: Optional[str] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Permanently delete a job opening. Destructive — this cannot be undone.

    For day-to-day workflows, prefer close_job_opening, which preserves the
    opening's history. Only use this to remove openings that were created in
    error.

    Args:
        opening_id: Numeric ID of the opening to delete
        confirm: Must be set to True to actually perform the deletion.
            Acts as a safety guard.
        on_behalf_of: Greenhouse user ID to attribute the action to.
            Falls back to GREENHOUSE_USER_ID env var.

    Returns:
        Empty object on success
    """
    if not confirm:
        raise ValueError(
            "delete_job_opening is destructive and requires confirm=True. "
            "Consider close_job_opening instead, which preserves history."
        )
    try:
        gh_client = get_client()
        result = await gh_client.delete_job_opening(
            opening_id, on_behalf_of=on_behalf_of
        )
        if ctx:
            ctx.info(f"Deleted opening {opening_id}")
        return result
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to delete opening {opening_id}: {str(e)}")
        raise


@mcp.tool
async def list_close_reasons(
    per_page: int = 50, page: int = 1, auto_paginate: bool = False, ctx: Context = None
) -> List[Dict[str, Any]]:
    """
    List close reasons configured in the organization.

    Use the returned IDs as close_reason_id when closing an opening or
    rejecting an application.

    Args:
        per_page: Results per page
        page: Page number
        auto_paginate: If true, follow Link headers to fetch all pages

    Returns:
        List of close reason objects with id and name
    """
    try:
        gh_client = get_client()
        reasons = await gh_client.list_close_reasons(
            per_page=per_page, page=page, auto_paginate=auto_paginate
        )
        if ctx:
            ctx.info(f"Retrieved {len(reasons)} close reasons")
        return reasons
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to list close reasons: {str(e)}")
        raise


@mcp.tool
async def list_job_stages(
    per_page: int = 50,
    page: int = 1,
    active: Optional[bool] = None,
    auto_paginate: bool = False,
    ctx: Context = None,
) -> List[Dict[str, Any]]:
    """
    List all job stages defined in the organization.

    Job stages are the steps of an interview plan (e.g. "Phone Screen",
    "Technical Interview", "Offer"). Use this when you need a stage ID for
    advance_application, or to look up the structure of an interview plan.

    Args:
        per_page: Results per page
        page: Page number
        active: If true, only return active stages
        auto_paginate: If true, follow Link headers to fetch all pages

    Returns:
        List of job stage objects (id, name, position, active, schedulable, ...)
    """
    try:
        gh_client = get_client()
        stages = await gh_client.list_job_stages(
            per_page=per_page,
            page=page,
            active=active,
            auto_paginate=auto_paginate,
        )
        if ctx:
            ctx.info(f"Retrieved {len(stages)} job stages")
        return stages
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to list job stages: {str(e)}")
        raise


@mcp.tool
async def list_job_stages_for_job(
    job_id: int,
    per_page: int = 50,
    page: int = 1,
    auto_paginate: bool = False,
    ctx: Context = None,
) -> List[Dict[str, Any]]:
    """
    List the stages of a specific job's interview plan, in order.

    This is the right tool to call before advance_application — the
    application's current stage will be one of the items returned here,
    and the next stage to advance to is the one with the next position.

    Args:
        job_id: ID of the job
        per_page: Results per page
        page: Page number
        auto_paginate: If true, follow Link headers to fetch all pages

    Returns:
        List of job stage objects ordered by position
    """
    try:
        gh_client = get_client()
        stages = await gh_client.list_job_stages_for_job(
            job_id,
            per_page=per_page,
            page=page,
            auto_paginate=auto_paginate,
        )
        if ctx:
            ctx.info(f"Retrieved {len(stages)} stages for job {job_id}")
        return stages
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to list stages for job {job_id}: {str(e)}")
        raise


@mcp.tool
async def get_job_stage(stage_id: int, ctx: Context = None) -> Dict[str, Any]:
    """
    Retrieve a single job stage, including its interview kit if present.

    Args:
        stage_id: Numeric ID of the job stage

    Returns:
        Job stage object
    """
    try:
        gh_client = get_client()
        stage = await gh_client.get_job_stage(stage_id)
        if ctx:
            ctx.info(f"Retrieved stage: {stage.get('name', stage_id)}")
        return stage
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to get stage {stage_id}: {str(e)}")
        raise


@mcp.tool
async def get_job_hiring_team(job_id: int, ctx: Context = None) -> Dict[str, Any]:
    """
    Retrieve the hiring team for a job — the recruiters, coordinators,
    hiring managers, and sourcers attached to it.

    Args:
        job_id: ID of the job

    Returns:
        Object with role-keyed lists (recruiters, coordinators,
        hiring_managers, sourcers), each containing user objects.
    """
    try:
        gh_client = get_client()
        team = await gh_client.get_job_hiring_team(job_id)
        if ctx:
            ctx.info(f"Retrieved hiring team for job {job_id}")
        return team
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to get hiring team for job {job_id}: {str(e)}")
        raise


def _build_hiring_team_payload(
    recruiter_ids: Optional[List[int]],
    coordinator_ids: Optional[List[int]],
    hiring_manager_ids: Optional[List[int]],
    sourcer_ids: Optional[List[int]],
) -> Dict[str, List[Dict[str, int]]]:
    payload: Dict[str, List[Dict[str, int]]] = {}
    if recruiter_ids is not None:
        payload["recruiters"] = [{"id": uid} for uid in recruiter_ids]
    if coordinator_ids is not None:
        payload["coordinators"] = [{"id": uid} for uid in coordinator_ids]
    if hiring_manager_ids is not None:
        payload["hiring_managers"] = [{"id": uid} for uid in hiring_manager_ids]
    if sourcer_ids is not None:
        payload["sourcers"] = [{"id": uid} for uid in sourcer_ids]
    return payload


@mcp.tool
async def add_hiring_team_members(
    job_id: int,
    recruiter_ids: Optional[List[int]] = None,
    coordinator_ids: Optional[List[int]] = None,
    hiring_manager_ids: Optional[List[int]] = None,
    sourcer_ids: Optional[List[int]] = None,
    on_behalf_of: Optional[str] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Append members to a job's hiring team without removing existing ones.

    Provide user IDs grouped by role. Any role you don't supply is left
    unchanged. Use replace_hiring_team if you want to wholesale overwrite
    the team.

    Args:
        job_id: ID of the job
        recruiter_ids: User IDs to add as recruiters
        coordinator_ids: User IDs to add as coordinators
        hiring_manager_ids: User IDs to add as hiring managers
        sourcer_ids: User IDs to add as sourcers
        on_behalf_of: Greenhouse user ID to attribute the action to.
            Falls back to GREENHOUSE_USER_ID env var.

    Returns:
        Updated hiring team object
    """
    payload = _build_hiring_team_payload(
        recruiter_ids, coordinator_ids, hiring_manager_ids, sourcer_ids
    )
    if not payload:
        raise ValueError(
            "add_hiring_team_members requires at least one of recruiter_ids, "
            "coordinator_ids, hiring_manager_ids, or sourcer_ids"
        )
    try:
        gh_client = get_client()
        result = await gh_client.add_hiring_team_members(
            job_id, payload, on_behalf_of=on_behalf_of
        )
        if ctx:
            ctx.info(f"Added hiring team members to job {job_id}")
        return result
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to add hiring team members to job {job_id}: {str(e)}")
        raise


@mcp.tool
async def replace_hiring_team(
    job_id: int,
    recruiter_ids: Optional[List[int]] = None,
    coordinator_ids: Optional[List[int]] = None,
    hiring_manager_ids: Optional[List[int]] = None,
    sourcer_ids: Optional[List[int]] = None,
    on_behalf_of: Optional[str] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Wholesale-replace a job's hiring team. Roles you supply are overwritten;
    roles you omit become empty lists. Get the current team first with
    get_job_hiring_team if you want to preserve members in roles you're not
    changing.

    Args:
        job_id: ID of the job
        recruiter_ids: Full set of recruiter user IDs (replaces existing)
        coordinator_ids: Full set of coordinator user IDs
        hiring_manager_ids: Full set of hiring manager user IDs
        sourcer_ids: Full set of sourcer user IDs
        on_behalf_of: Greenhouse user ID to attribute the action to.
            Falls back to GREENHOUSE_USER_ID env var.

    Returns:
        Updated hiring team object
    """
    payload = _build_hiring_team_payload(
        recruiter_ids, coordinator_ids, hiring_manager_ids, sourcer_ids
    )
    try:
        gh_client = get_client()
        result = await gh_client.replace_hiring_team(
            job_id, payload, on_behalf_of=on_behalf_of
        )
        if ctx:
            ctx.info(f"Replaced hiring team for job {job_id}")
        return result
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to replace hiring team for job {job_id}: {str(e)}")
        raise


@mcp.tool
async def remove_hiring_team_member(
    job_id: int, user_id: int, on_behalf_of: Optional[str] = None, ctx: Context = None
) -> Dict[str, Any]:
    """
    Remove a single user from a job's hiring team.

    Args:
        job_id: ID of the job
        user_id: ID of the Greenhouse user to remove
        on_behalf_of: Greenhouse user ID to attribute the action to.
            Falls back to GREENHOUSE_USER_ID env var.

    Returns:
        Empty object on success
    """
    try:
        gh_client = get_client()
        result = await gh_client.remove_hiring_team_member(
            job_id, user_id, on_behalf_of=on_behalf_of
        )
        if ctx:
            ctx.info(f"Removed user {user_id} from hiring team of job {job_id}")
        return result
    except Exception as e:
        if ctx:
            ctx.error(f"Failed to remove user {user_id} from job {job_id}: {str(e)}")
        raise


def main():
    """Main entry point for the MCP server."""
    import sys

    if not os.getenv("GREENHOUSE_API_KEY"):
        print(
            "Error: GREENHOUSE_API_KEY environment variable is required",
            file=sys.stderr,
        )
        print("Please set it in your .env file or environment.", file=sys.stderr)
        sys.exit(1)

    mcp.run()


if __name__ == "__main__":
    main()
