from unittest.mock import AsyncMock

import pytest

import src.greenhouse_mcp as gh_mcp


@pytest.fixture
def fake_client(monkeypatch):
    """Replace the cached GreenhouseClient with an AsyncMock."""
    client = AsyncMock()
    monkeypatch.setattr(gh_mcp, "client", client)
    return client


async def test_list_jobs_passes_filters_through(fake_client):
    fake_client.list_jobs.return_value = [{"id": 1}]

    result = await gh_mcp.list_jobs(
        per_page=25,
        page=2,
        status="open",
        created_after="2026-01-01",
        auto_paginate=True,
    )

    assert result == [{"id": 1}]
    fake_client.list_jobs.assert_awaited_once_with(
        per_page=25,
        page=2,
        status="open",
        created_after="2026-01-01",
        created_before=None,
        auto_paginate=True,
    )


async def test_create_job_strips_none_and_sends_template(fake_client):
    fake_client.create_job.return_value = {"id": 99}

    result = await gh_mcp.create_job(
        template_job_id=10,
        job_name="Senior Eng",
        number_of_openings=2,
        on_behalf_of="42",
    )

    assert result == {"id": 99}
    fake_client.create_job.assert_awaited_once_with(
        {"template_job_id": 10, "job_name": "Senior Eng", "number_of_openings": 2},
        on_behalf_of="42",
    )


async def test_update_job_raises_when_no_fields_provided(fake_client):
    with pytest.raises(ValueError, match="at least one of"):
        await gh_mcp.update_job(job_id=1)
    fake_client.update_job.assert_not_called()


async def test_update_job_sends_only_provided_fields(fake_client):
    fake_client.update_job.return_value = {"id": 1}
    await gh_mcp.update_job(job_id=1, name="new", department_id=7)
    fake_client.update_job.assert_awaited_once_with(
        1, {"name": "new", "department_id": 7}, on_behalf_of=None
    )


async def test_advance_application_forwards_args(fake_client):
    fake_client.advance_application.return_value = {"ok": True}
    await gh_mcp.advance_application(
        application_id=5, from_stage_id=10, to_stage_id=20, on_behalf_of="42"
    )
    fake_client.advance_application.assert_awaited_once_with(
        application_id=5, from_stage_id=10, to_stage_id=20, on_behalf_of="42"
    )


async def test_close_job_opening_delegates_to_update(fake_client):
    fake_client.update_job_opening.return_value = {"id": 7, "status": "closed"}
    await gh_mcp.close_job_opening(opening_id=7, close_reason_id=3, on_behalf_of="42")
    fake_client.update_job_opening.assert_awaited_once_with(
        7, {"status": "closed", "close_reason_id": 3}, on_behalf_of="42"
    )


async def test_reopen_job_opening_sets_status_open(fake_client):
    fake_client.update_job_opening.return_value = {"id": 7, "status": "open"}
    await gh_mcp.reopen_job_opening(opening_id=7, on_behalf_of="42")
    fake_client.update_job_opening.assert_awaited_once_with(
        7, {"status": "open"}, on_behalf_of="42"
    )


EXPECTED_TOOLS = {
    "list_jobs",
    "get_job",
    "create_job",
    "update_job",
    "list_job_posts_for_job",
    "list_candidates",
    "get_candidate",
    "create_candidate",
    "update_candidate",
    "add_note_to_candidate",
    "list_applications",
    "get_application",
    "advance_application",
    "reject_application",
    "add_note_to_application",
    "list_job_openings",
    "get_job_opening",
    "create_job_openings",
    "update_job_opening",
    "close_job_opening",
    "reopen_job_opening",
    "delete_job_opening",
    "list_close_reasons",
    "list_job_stages",
    "list_job_stages_for_job",
    "get_job_stage",
    "get_job_hiring_team",
    "add_hiring_team_members",
    "replace_hiring_team",
    "remove_hiring_team_member",
    "list_departments",
    "list_offices",
    "list_users",
}


async def test_all_expected_tools_registered():
    tools = await gh_mcp.mcp.list_tools()
    names = {t.name if hasattr(t, "name") else str(t) for t in tools}
    missing = EXPECTED_TOOLS - names
    assert not missing, f"missing tools: {sorted(missing)}"
