import asyncio
import base64
import os
import re
import time
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()


WRITE_METHODS = {"POST", "PATCH", "PUT", "DELETE"}


class GreenhouseClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        on_behalf_of: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("GREENHOUSE_API_KEY")
        if not self.api_key:
            raise ValueError("Greenhouse API key is required")

        self.on_behalf_of = on_behalf_of or os.getenv("GREENHOUSE_USER_ID")

        self.base_url = os.getenv(
            "GREENHOUSE_BASE_URL", "https://harvest.greenhouse.io/v1"
        )

        auth_string = base64.b64encode(f"{self.api_key}:".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {auth_string}",
            "Content-Type": "application/json",
        }

        self._rate_limit_window = 10
        self._rate_limit_max = 50
        self._request_times: List[float] = []
        self._rate_lock = asyncio.Lock()

    async def _rate_limit(self) -> None:
        async with self._rate_lock:
            now = time.monotonic()
            cutoff = now - self._rate_limit_window
            self._request_times = [t for t in self._request_times if t > cutoff]

            if len(self._request_times) >= self._rate_limit_max:
                sleep_time = self._rate_limit_window - (now - self._request_times[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                now = time.monotonic()
                cutoff = now - self._rate_limit_window
                self._request_times = [t for t in self._request_times if t > cutoff]

            self._request_times.append(now)

    def _build_headers(
        self,
        method: str,
        on_behalf_of: Optional[str],
    ) -> Dict[str, str]:
        headers = self.headers.copy()
        if method.upper() in WRITE_METHODS:
            user_id = on_behalf_of or self.on_behalf_of
            if not user_id:
                raise ValueError(
                    "GREENHOUSE_USER_ID is required for write operations. "
                    "Set the GREENHOUSE_USER_ID environment variable or pass "
                    "on_behalf_of explicitly."
                )
            headers["On-Behalf-Of"] = str(user_id)
        elif on_behalf_of or self.on_behalf_of:
            headers["On-Behalf-Of"] = str(on_behalf_of or self.on_behalf_of)
        return headers

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        on_behalf_of: Optional[str] = None,
        return_response: bool = False,
        absolute_url: Optional[str] = None,
    ) -> Any:
        await self._rate_limit()

        url = absolute_url or f"{self.base_url}/{endpoint}"
        headers = self._build_headers(method, on_behalf_of)

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=30.0,
            )

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 10))
                await asyncio.sleep(retry_after)
                return await self._make_request(
                    method,
                    endpoint,
                    params=params,
                    json_data=json_data,
                    on_behalf_of=on_behalf_of,
                    return_response=return_response,
                    absolute_url=absolute_url,
                )

            response.raise_for_status()

            if return_response:
                return response

            if response.status_code == 204 or not response.content:
                return {}

            return response.json()

    @staticmethod
    def _parse_next_link(link_header: Optional[str]) -> Optional[str]:
        if not link_header:
            return None
        for part in link_header.split(","):
            match = re.match(r"\s*<([^>]+)>\s*;\s*rel=\"?next\"?", part)
            if match:
                return match.group(1)
        return None

    async def _paginate(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        on_behalf_of: Optional[str] = None,
        max_pages: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        next_url: Optional[str] = None
        page_count = 0

        while True:
            response = await self._make_request(
                "GET",
                endpoint if next_url is None else "",
                params=params if next_url is None else None,
                on_behalf_of=on_behalf_of,
                return_response=True,
                absolute_url=next_url,
            )

            data = response.json() if response.content else []
            if isinstance(data, list):
                results.extend(data)
            else:
                results.append(data)

            page_count += 1
            if max_pages is not None and page_count >= max_pages:
                break

            next_url = self._parse_next_link(response.headers.get("Link"))
            if not next_url:
                break

        return results

    async def list_jobs(
        self,
        per_page: int = 50,
        page: int = 1,
        created_before: Optional[str] = None,
        created_after: Optional[str] = None,
        status: Optional[str] = None,
        auto_paginate: bool = False,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"per_page": per_page, "page": page}
        if created_before:
            params["created_before"] = created_before
        if created_after:
            params["created_after"] = created_after
        if status:
            params["status"] = status

        if auto_paginate:
            return await self._paginate("jobs", params=params)
        return await self._make_request("GET", "jobs", params=params)

    async def get_job(self, job_id: int) -> Dict[str, Any]:
        return await self._make_request("GET", f"jobs/{job_id}")

    async def create_job(
        self,
        data: Dict[str, Any],
        on_behalf_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._make_request(
            "POST", "jobs", json_data=data, on_behalf_of=on_behalf_of
        )

    async def update_job(
        self,
        job_id: int,
        data: Dict[str, Any],
        on_behalf_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._make_request(
            "PATCH",
            f"jobs/{job_id}",
            json_data=data,
            on_behalf_of=on_behalf_of,
        )

    async def list_job_posts_for_job(
        self,
        job_id: int,
        per_page: int = 50,
        page: int = 1,
        active: Optional[bool] = None,
        live: Optional[bool] = None,
        full_content: Optional[bool] = None,
        auto_paginate: bool = False,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"per_page": per_page, "page": page}
        if active is not None:
            params["active"] = "true" if active else "false"
        if live is not None:
            params["live"] = "true" if live else "false"
        if full_content is not None:
            params["full_content"] = "true" if full_content else "false"
        endpoint = f"jobs/{job_id}/job_posts"
        if auto_paginate:
            return await self._paginate(endpoint, params=params)
        return await self._make_request("GET", endpoint, params=params)

    async def list_job_posts(
        self,
        per_page: int = 50,
        page: int = 1,
        active: Optional[bool] = None,
        live: Optional[bool] = None,
        internal: Optional[bool] = None,
        full_content: Optional[bool] = None,
        skip_count: Optional[bool] = None,
        created_before: Optional[str] = None,
        created_after: Optional[str] = None,
        updated_before: Optional[str] = None,
        updated_after: Optional[str] = None,
        auto_paginate: bool = False,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"per_page": per_page, "page": page}
        if active is not None:
            params["active"] = "true" if active else "false"
        if live is not None:
            params["live"] = "true" if live else "false"
        if internal is not None:
            params["internal"] = "true" if internal else "false"
        if full_content is not None:
            params["full_content"] = "true" if full_content else "false"
        if skip_count is not None:
            params["skip_count"] = "true" if skip_count else "false"
        if created_before:
            params["created_before"] = created_before
        if created_after:
            params["created_after"] = created_after
        if updated_before:
            params["updated_before"] = updated_before
        if updated_after:
            params["updated_after"] = updated_after

        if auto_paginate:
            return await self._paginate("job_posts", params=params)
        return await self._make_request("GET", "job_posts", params=params)

    async def get_job_post(
        self,
        job_post_id: int,
        full_content: Optional[bool] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if full_content is not None:
            params["full_content"] = "true" if full_content else "false"
        return await self._make_request(
            "GET", f"job_posts/{job_post_id}", params=params or None
        )

    async def list_job_post_custom_locations(
        self,
        job_post_id: int,
    ) -> List[Dict[str, Any]]:
        return await self._make_request(
            "GET", f"job_posts/{job_post_id}/custom_locations"
        )

    async def update_job_post(
        self,
        job_post_id: int,
        data: Dict[str, Any],
        on_behalf_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        absolute_url = f"{self._v2_base()}/job_posts/{job_post_id}"
        return await self._make_request(
            "PATCH",
            "",
            json_data=data,
            on_behalf_of=on_behalf_of,
            absolute_url=absolute_url,
        )

    async def update_job_post_status(
        self,
        job_post_id: int,
        status: str,
        on_behalf_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        absolute_url = f"{self._v2_base()}/job_posts/{job_post_id}/status"
        return await self._make_request(
            "PATCH",
            "",
            json_data={"status": status},
            on_behalf_of=on_behalf_of,
            absolute_url=absolute_url,
        )

    async def list_candidates(
        self,
        per_page: int = 50,
        page: int = 1,
        created_before: Optional[str] = None,
        created_after: Optional[str] = None,
        email: Optional[str] = None,
        candidate_ids: Optional[List[int]] = None,
        auto_paginate: bool = False,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"per_page": per_page, "page": page}
        if created_before:
            params["created_before"] = created_before
        if created_after:
            params["created_after"] = created_after
        if email:
            params["email"] = email
        if candidate_ids:
            params["candidate_ids"] = ",".join(map(str, candidate_ids))

        if auto_paginate:
            return await self._paginate("candidates", params=params)
        return await self._make_request("GET", "candidates", params=params)

    async def get_candidate(self, candidate_id: int) -> Dict[str, Any]:
        return await self._make_request("GET", f"candidates/{candidate_id}")

    async def create_candidate(
        self,
        candidate_data: Dict[str, Any],
        on_behalf_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._make_request(
            "POST", "candidates", json_data=candidate_data, on_behalf_of=on_behalf_of
        )

    async def update_candidate(
        self,
        candidate_id: int,
        candidate_data: Dict[str, Any],
        on_behalf_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._make_request(
            "PATCH",
            f"candidates/{candidate_id}",
            json_data=candidate_data,
            on_behalf_of=on_behalf_of,
        )

    async def list_applications(
        self,
        per_page: int = 50,
        page: int = 1,
        created_before: Optional[str] = None,
        created_after: Optional[str] = None,
        job_id: Optional[int] = None,
        candidate_id: Optional[int] = None,
        status: Optional[str] = None,
        auto_paginate: bool = False,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"per_page": per_page, "page": page}
        if created_before:
            params["created_before"] = created_before
        if created_after:
            params["created_after"] = created_after
        if job_id:
            params["job_id"] = job_id
        if candidate_id:
            params["candidate_id"] = candidate_id
        if status:
            params["status"] = status

        if auto_paginate:
            return await self._paginate("applications", params=params)
        return await self._make_request("GET", "applications", params=params)

    async def get_application(self, application_id: int) -> Dict[str, Any]:
        return await self._make_request("GET", f"applications/{application_id}")

    async def advance_application(
        self,
        application_id: int,
        from_stage_id: int,
        to_stage_id: Optional[int] = None,
        on_behalf_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {"from_stage_id": from_stage_id}
        if to_stage_id:
            data["to_stage_id"] = to_stage_id

        return await self._make_request(
            "POST",
            f"applications/{application_id}/advance",
            json_data=data,
            on_behalf_of=on_behalf_of,
        )

    async def reject_application(
        self,
        application_id: int,
        rejection_reason_id: Optional[int] = None,
        notes: Optional[str] = None,
        rejection_email_id: Optional[int] = None,
        on_behalf_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        if rejection_reason_id:
            data["rejection_reason_id"] = rejection_reason_id
        if notes:
            data["notes"] = notes
        if rejection_email_id:
            data["rejection_email_send_email_at"] = rejection_email_id

        return await self._make_request(
            "POST",
            f"applications/{application_id}/reject",
            json_data=data,
            on_behalf_of=on_behalf_of,
        )

    async def add_note_to_candidate(
        self,
        candidate_id: int,
        body: str,
        visibility: str = "private",
        on_behalf_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        data = {"body": body, "visibility": visibility}
        return await self._make_request(
            "POST",
            f"candidates/{candidate_id}/activity_feed/notes",
            json_data=data,
            on_behalf_of=on_behalf_of,
        )

    async def add_note_to_application(
        self,
        application_id: int,
        body: str,
        visibility: str = "private",
        on_behalf_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        data = {"body": body, "visibility": visibility}
        return await self._make_request(
            "POST",
            f"applications/{application_id}/notes",
            json_data=data,
            on_behalf_of=on_behalf_of,
        )

    async def list_departments(
        self,
        per_page: int = 50,
        page: int = 1,
        auto_paginate: bool = False,
    ) -> List[Dict[str, Any]]:
        params = {"per_page": per_page, "page": page}
        if auto_paginate:
            return await self._paginate("departments", params=params)
        return await self._make_request("GET", "departments", params=params)

    async def list_offices(
        self,
        per_page: int = 50,
        page: int = 1,
        auto_paginate: bool = False,
    ) -> List[Dict[str, Any]]:
        params = {"per_page": per_page, "page": page}
        if auto_paginate:
            return await self._paginate("offices", params=params)
        return await self._make_request("GET", "offices", params=params)

    async def list_users(
        self,
        per_page: int = 50,
        page: int = 1,
        email: Optional[str] = None,
        auto_paginate: bool = False,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"per_page": per_page, "page": page}
        if email:
            params["email"] = email
        if auto_paginate:
            return await self._paginate("users", params=params)
        return await self._make_request("GET", "users", params=params)

    async def list_job_openings(
        self,
        per_page: int = 50,
        page: int = 1,
        status: Optional[str] = None,
        opening_id: Optional[str] = None,
        skip_count: Optional[bool] = None,
        auto_paginate: bool = False,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"per_page": per_page, "page": page}
        if status:
            params["status"] = status
        if opening_id:
            params["opening_id"] = opening_id
        if skip_count is not None:
            params["skip_count"] = "true" if skip_count else "false"
        if auto_paginate:
            return await self._paginate("job_openings", params=params)
        return await self._make_request("GET", "job_openings", params=params)

    async def get_job_opening(
        self,
        job_id: int,
        opening_id: int,
    ) -> Dict[str, Any]:
        return await self._make_request("GET", f"jobs/{job_id}/openings/{opening_id}")

    async def create_job_openings(
        self,
        job_id: int,
        openings: List[Dict[str, Any]],
        on_behalf_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._make_request(
            "POST",
            f"jobs/{job_id}/openings",
            json_data={"openings": openings},
            on_behalf_of=on_behalf_of,
        )

    async def update_job_opening(
        self,
        opening_id: int,
        data: Dict[str, Any],
        on_behalf_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._make_request(
            "PATCH",
            f"job_openings/{opening_id}",
            json_data=data,
            on_behalf_of=on_behalf_of,
        )

    async def delete_job_opening(
        self,
        opening_id: int,
        on_behalf_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        absolute_url = f"{self._v2_base()}/job_openings/{opening_id}"
        return await self._make_request(
            "DELETE",
            "",
            on_behalf_of=on_behalf_of,
            absolute_url=absolute_url,
        )

    def _v2_base(self) -> str:
        return self.base_url.rstrip("/").rsplit("/", 1)[0] + "/v2"

    async def list_close_reasons(
        self,
        per_page: int = 50,
        page: int = 1,
        auto_paginate: bool = False,
    ) -> List[Dict[str, Any]]:
        params = {"per_page": per_page, "page": page}
        if auto_paginate:
            return await self._paginate("close_reasons", params=params)
        return await self._make_request("GET", "close_reasons", params=params)

    async def list_job_stages(
        self,
        per_page: int = 50,
        page: int = 1,
        active: Optional[bool] = None,
        auto_paginate: bool = False,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"per_page": per_page, "page": page}
        if active is not None:
            params["active"] = "true" if active else "false"
        if auto_paginate:
            return await self._paginate("job_stages", params=params)
        return await self._make_request("GET", "job_stages", params=params)

    async def list_job_stages_for_job(
        self,
        job_id: int,
        per_page: int = 50,
        page: int = 1,
        auto_paginate: bool = False,
    ) -> List[Dict[str, Any]]:
        params = {"per_page": per_page, "page": page}
        endpoint = f"jobs/{job_id}/stages"
        if auto_paginate:
            return await self._paginate(endpoint, params=params)
        return await self._make_request("GET", endpoint, params=params)

    async def get_job_stage(self, stage_id: int) -> Dict[str, Any]:
        return await self._make_request("GET", f"job_stages/{stage_id}")

    async def get_job_hiring_team(self, job_id: int) -> Dict[str, Any]:
        return await self._make_request("GET", f"jobs/{job_id}/hiring_team")

    async def add_hiring_team_members(
        self,
        job_id: int,
        members: Dict[str, List[Dict[str, Any]]],
        on_behalf_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._make_request(
            "POST",
            f"jobs/{job_id}/hiring_team",
            json_data=members,
            on_behalf_of=on_behalf_of,
        )

    async def replace_hiring_team(
        self,
        job_id: int,
        members: Dict[str, List[Dict[str, Any]]],
        on_behalf_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._make_request(
            "PUT",
            f"jobs/{job_id}/hiring_team",
            json_data=members,
            on_behalf_of=on_behalf_of,
        )

    async def remove_hiring_team_member(
        self,
        job_id: int,
        user_id: int,
        on_behalf_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._make_request(
            "DELETE",
            f"jobs/{job_id}/hiring_team/{user_id}",
            on_behalf_of=on_behalf_of,
        )
