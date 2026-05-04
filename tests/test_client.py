import asyncio
import base64

import httpx
import pytest
import respx

from src.greenhouse_client import GreenhouseClient

BASE_URL = "https://harvest.greenhouse.io/v1"


def test_requires_api_key(monkeypatch):
    monkeypatch.delenv("GREENHOUSE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="API key is required"):
        GreenhouseClient(api_key=None)


def test_auth_header_is_base64_basic():
    client = GreenhouseClient(api_key="my-secret-key")
    expected = base64.b64encode(b"my-secret-key:").decode()
    assert client.headers["Authorization"] == f"Basic {expected}"
    assert client.headers["Content-Type"] == "application/json"


@respx.mock
async def test_get_does_not_require_on_behalf_of():
    client = GreenhouseClient(api_key="k", on_behalf_of=None)
    route = respx.get(f"{BASE_URL}/jobs/1").mock(
        return_value=httpx.Response(200, json={"id": 1})
    )
    result = await client.get_job(1)
    assert result == {"id": 1}
    assert "On-Behalf-Of" not in route.calls.last.request.headers


@respx.mock
async def test_write_without_on_behalf_of_raises(monkeypatch):
    monkeypatch.delenv("GREENHOUSE_USER_ID", raising=False)
    client = GreenhouseClient(api_key="k", on_behalf_of=None)
    with pytest.raises(ValueError, match="GREENHOUSE_USER_ID is required"):
        await client.create_job({"template_job_id": 5})


@respx.mock
async def test_write_uses_explicit_on_behalf_of():
    client = GreenhouseClient(api_key="k", on_behalf_of="42")
    route = respx.post(f"{BASE_URL}/jobs").mock(
        return_value=httpx.Response(201, json={"id": 7})
    )
    await client.create_job({"template_job_id": 5}, on_behalf_of="123")
    request = route.calls.last.request
    assert request.headers["On-Behalf-Of"] == "123"


@respx.mock
async def test_write_falls_back_to_default_on_behalf_of():
    client = GreenhouseClient(api_key="k", on_behalf_of="42")
    route = respx.post(f"{BASE_URL}/jobs").mock(
        return_value=httpx.Response(201, json={"id": 7})
    )
    await client.create_job({"template_job_id": 5})
    assert route.calls.last.request.headers["On-Behalf-Of"] == "42"


@respx.mock
async def test_get_passes_on_behalf_of_when_set():
    client = GreenhouseClient(api_key="k", on_behalf_of="42")
    route = respx.get(f"{BASE_URL}/jobs/9").mock(
        return_value=httpx.Response(200, json={"id": 9})
    )
    await client.get_job(9)
    assert route.calls.last.request.headers["On-Behalf-Of"] == "42"


@respx.mock
async def test_204_returns_empty_dict():
    client = GreenhouseClient(api_key="k", on_behalf_of="42")
    respx.delete(f"{BASE_URL}/jobs/3/hiring_team/4").mock(
        return_value=httpx.Response(204)
    )
    result = await client.remove_hiring_team_member(3, 4)
    assert result == {}


@respx.mock
async def test_429_retries_after_retry_after():
    client = GreenhouseClient(api_key="k")
    respx.get(f"{BASE_URL}/jobs/1").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json={"id": 1}),
        ]
    )
    result = await client.get_job(1)
    assert result == {"id": 1}


@respx.mock
async def test_4xx_raises():
    client = GreenhouseClient(api_key="k")
    respx.get(f"{BASE_URL}/jobs/404").mock(
        return_value=httpx.Response(404, json={"error": "not found"})
    )
    with pytest.raises(httpx.HTTPStatusError):
        await client.get_job(404)


def test_parse_next_link_extracts_next_url():
    link = (
        '<https://harvest.greenhouse.io/v1/jobs?page=2>; rel="next", '
        '<https://harvest.greenhouse.io/v1/jobs?page=10>; rel="last"'
    )
    assert (
        GreenhouseClient._parse_next_link(link)
        == "https://harvest.greenhouse.io/v1/jobs?page=2"
    )


def test_parse_next_link_returns_none_when_no_next():
    link = '<https://harvest.greenhouse.io/v1/jobs?page=10>; rel="last"'
    assert GreenhouseClient._parse_next_link(link) is None
    assert GreenhouseClient._parse_next_link(None) is None


@respx.mock
async def test_paginate_follows_link_header():
    client = GreenhouseClient(api_key="k")
    page1 = httpx.Response(
        200,
        json=[{"id": 1}, {"id": 2}],
        headers={"Link": f'<{BASE_URL}/jobs?page=2>; rel="next"'},
    )
    page2 = httpx.Response(200, json=[{"id": 3}])
    respx.get(f"{BASE_URL}/jobs", params={"per_page": 50, "page": 1}).mock(
        return_value=page1
    )
    respx.get(f"{BASE_URL}/jobs", params={"page": 2}).mock(return_value=page2)

    results = await client.list_jobs(auto_paginate=True)
    assert [r["id"] for r in results] == [1, 2, 3]


@respx.mock
async def test_list_jobs_passes_filters_as_query_params():
    client = GreenhouseClient(api_key="k")
    route = respx.get(f"{BASE_URL}/jobs").mock(
        return_value=httpx.Response(200, json=[])
    )
    await client.list_jobs(per_page=25, page=2, status="open")
    request = route.calls.last.request
    assert request.url.params["per_page"] == "25"
    assert request.url.params["page"] == "2"
    assert request.url.params["status"] == "open"


@respx.mock
async def test_delete_job_opening_targets_v2_endpoint():
    client = GreenhouseClient(api_key="k", on_behalf_of="1")
    route = respx.delete("https://harvest.greenhouse.io/v2/job_openings/55").mock(
        return_value=httpx.Response(204)
    )
    await client.delete_job_opening(55)
    assert route.called


@respx.mock
async def test_list_job_posts_passes_filters_as_query_params():
    client = GreenhouseClient(api_key="k")
    route = respx.get(f"{BASE_URL}/job_posts").mock(
        return_value=httpx.Response(200, json=[])
    )
    await client.list_job_posts(
        per_page=10,
        page=3,
        active=True,
        live=False,
        internal=True,
        full_content=True,
        skip_count=True,
        created_after="2026-01-01",
        updated_before="2026-05-01",
    )
    params = route.calls.last.request.url.params
    assert params["per_page"] == "10"
    assert params["page"] == "3"
    assert params["active"] == "true"
    assert params["live"] == "false"
    assert params["internal"] == "true"
    assert params["full_content"] == "true"
    assert params["skip_count"] == "true"
    assert params["created_after"] == "2026-01-01"
    assert params["updated_before"] == "2026-05-01"


@respx.mock
async def test_get_job_post_passes_full_content():
    client = GreenhouseClient(api_key="k")
    route = respx.get(f"{BASE_URL}/job_posts/42").mock(
        return_value=httpx.Response(200, json={"id": 42})
    )
    await client.get_job_post(42, full_content=True)
    assert route.calls.last.request.url.params["full_content"] == "true"


@respx.mock
async def test_get_job_post_omits_params_when_none():
    client = GreenhouseClient(api_key="k")
    route = respx.get(f"{BASE_URL}/job_posts/42").mock(
        return_value=httpx.Response(200, json={"id": 42})
    )
    await client.get_job_post(42)
    assert route.calls.last.request.url.query == b""


@respx.mock
async def test_list_job_post_custom_locations():
    client = GreenhouseClient(api_key="k")
    route = respx.get(f"{BASE_URL}/job_posts/42/custom_locations").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "value": "Boston"}])
    )
    result = await client.list_job_post_custom_locations(42)
    assert route.called
    assert result == [{"id": 1, "value": "Boston"}]


@respx.mock
async def test_update_job_post_targets_v2_endpoint():
    client = GreenhouseClient(api_key="k", on_behalf_of="42")
    route = respx.patch("https://harvest.greenhouse.io/v2/job_posts/9").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    await client.update_job_post(9, {"title": "New Title"})
    request = route.calls.last.request
    assert request.headers["On-Behalf-Of"] == "42"
    assert b'"title"' in request.content


@respx.mock
async def test_update_job_post_status_targets_v2_endpoint():
    client = GreenhouseClient(api_key="k", on_behalf_of="42")
    route = respx.patch("https://harvest.greenhouse.io/v2/job_posts/9/status").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    await client.update_job_post_status(9, "live")
    request = route.calls.last.request
    assert request.headers["On-Behalf-Of"] == "42"
    assert b'"status":"live"' in request.content.replace(b" ", b"")


async def test_rate_limiter_sleeps_when_window_full(monkeypatch):
    client = GreenhouseClient(api_key="k")
    client._rate_limit_max = 2
    client._rate_limit_window = 5

    # Pre-fill the window so the next call must wait.
    import time as _time

    now = _time.monotonic()
    client._request_times = [now, now]

    sleeps: list[float] = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)
        # Simulate time passing so the prefill ages out and the loop exits.
        client._request_times = []

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    await client._rate_limit()
    assert sleeps, "rate limiter should have slept"
    assert sleeps[0] > 0
