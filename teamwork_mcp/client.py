"""Teamwork API client for MCP server."""

import logging
import os
from typing import Any, Dict, List, Optional

from mcp_base import BaseAPIClient

LOGGER = logging.getLogger(__name__)


class TeamworkClient(BaseAPIClient):
    """Client for Teamwork.com API v3 with v1 fallback.
    
    Extends BaseAPIClient to inherit common HTTP request handling.
    This client expects to receive an OAuth access token and uses it
    to make authenticated requests to the Teamwork API.
    
    Note: Some operations (task list CRUD, comments) use v1 API endpoints
    as they aren't fully available in v3.
    """
    
    def __init__(self, access_token: str, installation_domain: str):
        """Initialize Teamwork client.
        
        Args:
            access_token: OAuth 2.0 access token
            installation_domain: Teamwork installation domain (e.g., "dynamic8.teamwork.com")
        """
        # Store installation domain for v1 API requests
        self.installation_domain = installation_domain
        # TeamworkClient uses dynamic base_url based on installation domain
        base_url = f"https://{installation_domain}/projects/api/v3"
        super().__init__(access_token=access_token, base_url=base_url)
    
    def _request_v1(
        self,
        method: str,
        path: str,
        params: dict = None,
        json_data: dict = None,
        timeout: int = None,
    ) -> Dict[str, Any]:
        """Make request to v1 API (some operations aren't available in v3).
        
        Uses direct URL construction to bypass v3 base_url.
        
        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            path: URL path (e.g., "/projects/123/tasklists.json")
            params: Query parameters
            json_data: JSON body data
            timeout: Request timeout
            
        Returns:
            Response JSON as dict
        """
        import requests
        
        url = f"https://{self.installation_domain}{path}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=timeout or self.DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            
            # Handle empty responses (204 No Content)
            if response.status_code == 204 or not response.content:
                return {"success": True}
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            self._logger.error(
                "%s v1 API error %d: %s",
                self.__class__.__name__,
                e.response.status_code,
                e.response.text,
            )
            raise RuntimeError(
                f"{self.__class__.__name__} v1 API error {e.response.status_code}: {e.response.text}"
            )
        except requests.exceptions.RequestException as e:
            self._logger.error("%s v1 request failed: %s", self.__class__.__name__, e)
            raise RuntimeError(f"{self.__class__.__name__} v1 request failed: {e}")
    
    # ===== Project Management =====
    
    def list_projects(
        self,
        page: int = 1,
        page_size: int = 25,
        include_details: bool = False,
    ) -> Dict[str, Any]:
        """List all projects.
        
        Args:
            page: Page number for pagination (default: 1)
            page_size: Number of results per page (default: 25)
            include_details: If True, return full project objects. If False (default),
                return minimal data (id, name, status, company) to reduce response size.
        
        Returns:
            Dictionary containing projects list and pagination metadata
        """
        response = self._request(
            "GET",
            "/projects.json",
            params={"page": page, "pageSize": page_size}
        )
        
        if not include_details:
            # Return minimal project data to reduce token usage
            minimal_projects = []
            for project in response.get("projects", []):
                minimal_projects.append({
                    "id": project.get("id"),
                    "name": project.get("name"),
                    "status": project.get("status"),
                    "company": (project.get("company") or {}).get("name"),
                })
            return {
                "projects": minimal_projects,
                "meta": response.get("meta", {}),
            }
        
        return response
    
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get project details."""
        return self._request("GET", f"/projects/{project_id}.json")
    
    def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new project."""
        payload = {"project": {"name": name}}
        if description:
            payload["project"]["description"] = description
        if start_date:
            payload["project"]["startDate"] = start_date
        if end_date:
            payload["project"]["endDate"] = end_date
            
        return self._request("POST", "/projects.json", json_data=payload)
    
    # ===== Task Management =====
    
    def list_tasks(
        self,
        project_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """List tasks, optionally filtered by project."""
        params = {"page": page, "pageSize": page_size}
        if project_id:
            params["projectId"] = project_id
        
        return self._request("GET", "/tasks.json", params=params)
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get task details."""
        return self._request("GET", f"/tasks/{task_id}.json")
    
    def create_task(
        self,
        name: str,
        tasklist_id: str,
        description: Optional[str] = None,
        due_date: Optional[str] = None,
        assignee_ids: Optional[List[str]] = None,
        priority: Optional[str] = None,
        estimated_minutes: Optional[int] = None,
        progress: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a new task.
        
        Args:
            name: Task name
            tasklist_id: Task list ID to create the task in
            description: Task description
            due_date: Due date in YYYY-MM-DD format
            assignee_ids: List of user IDs to assign
            priority: Priority level (low, medium, high)
            estimated_minutes: Estimated time to complete in minutes
            progress: Progress percentage (0=not started, 100=complete)
        """
        payload = {
            "task": {
                "name": name,
                "tasklistId": int(tasklist_id),
            }
        }
        if description:
            payload["task"]["description"] = description
        if due_date:
            payload["task"]["dueDate"] = due_date
        if assignee_ids:
            payload["task"]["assigneeIds"] = assignee_ids
        if priority:
            payload["task"]["priority"] = priority
        if estimated_minutes is not None:
            if estimated_minutes <= 0:
                raise ValueError("estimated_minutes must be a positive value")
            payload["task"]["estimatedMinutes"] = estimated_minutes
        if progress is not None:
            if not 0 <= progress <= 100:
                raise ValueError("progress must be between 0 and 100")
            payload["task"]["progress"] = progress
            
        return self._request("POST", f"/tasklists/{tasklist_id}/tasks.json", json_data=payload)
    
    def update_task(
        self,
        task_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        completed: Optional[bool] = None,
        due_date: Optional[str] = None,
        priority: Optional[str] = None,
        estimated_minutes: Optional[int] = None,
        progress: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Update an existing task.
        
        Args:
            task_id: Task ID to update
            name: New task name
            description: New description
            completed: Mark as completed
            due_date: New due date in YYYY-MM-DD format
            priority: Priority level (low, medium, high)
            estimated_minutes: Estimated time to complete in minutes
            progress: Progress percentage (0=not started, 100=complete)
        
        Note:
            When both completed and progress are provided, they must be consistent:
            completed=True requires progress=100, and progress=100 requires completed=True.
        """
        payload = {"task": {}}
        if name is not None:
            payload["task"]["name"] = name
        if description is not None:
            payload["task"]["description"] = description
        if completed is not None:
            payload["task"]["completed"] = completed
        if due_date is not None:
            payload["task"]["dueDate"] = due_date
        if priority is not None:
            payload["task"]["priority"] = priority
        if estimated_minutes is not None:
            if estimated_minutes <= 0:
                raise ValueError("estimated_minutes must be a positive value")
            payload["task"]["estimatedMinutes"] = estimated_minutes
        if progress is not None:
            if not 0 <= progress <= 100:
                raise ValueError("progress must be between 0 and 100")
            payload["task"]["progress"] = progress
        
        if completed is not None:
            payload["task"]["completed"] = completed
            
        return self._request("PATCH", f"/tasks/{task_id}.json", json_data=payload)
    
    def complete_task(self, task_id: str) -> Dict[str, Any]:
        """Mark a task as complete."""
        return self.update_task(task_id, completed=True)
    
    # ===== Time Tracking =====
    
    def list_time_entries(
        self,
        project_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """List time entries, optionally filtered by project."""
        params = {"page": page, "pageSize": page_size}
        if project_id:
            params["projectId"] = project_id
            
        return self._request("GET", "/time.json", params=params)
    
    def log_time(
        self,
        project_id: str,
        hours: float,
        description: str,
        date: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Log time entry."""
        payload = {
            "timeEntry": {
                "projectId": project_id,
                "hours": hours,
                "description": description,
            }
        }
        if date:
            payload["timeEntry"]["date"] = date
        if task_id:
            payload["timeEntry"]["taskId"] = task_id
            
        return self._request("POST", "/timers.json", json_data=payload)
    
    # ===== People Management =====
    
    def list_people(
        self,
        project_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """List people, optionally filtered by project."""
        params = {"page": page, "pageSize": page_size}
        if project_id:
            params["projectId"] = project_id
            
        return self._request("GET", "/people.json", params=params)
    
    def get_me(self) -> Dict[str, Any]:
        """Get current authenticated user information."""
        return self._request("GET", "/me.json")
    
    # ===== Planning Tools =====
    
    def get_my_tasks(
        self,
        user_id: str,
        date_filter: str = "within7",
        include_completed: bool = False,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """Get tasks assigned to a specific user with due date filtering.
        
        Args:
            user_id: User ID to filter tasks for
            date_filter: Date filter - overdue, today, thisweek, within7, within14, within30
            include_completed: Whether to include completed tasks
            page_size: Number of results (default 100)
        
        Returns:
            Dictionary containing filtered tasks optimized for planning
        """
        params = {
            "responsiblePartyIds": user_id,
            "filter": date_filter,
            "pageSize": page_size,
        }
        # Teamwork API requires explicit includeCompletedTasks parameter
        params["includeCompletedTasks"] = "true" if include_completed else "false"
        
        return self._request("GET", "/tasks.json", params=params)
    
    def get_project_summary(self, project_id: str) -> Dict[str, Any]:
        """Get a concise project health summary.
        
        Fetches project details and task statistics for planning and status reporting.
        
        Note: This method makes 4 API calls (project details + 3 task count queries).
        For projects with very high task counts, consider caching or rate limiting.
        
        Args:
            project_id: Project ID to summarize
        
        Returns:
            Dictionary containing project info, task statistics, and health status
        """
        # Get project details
        project = self._request("GET", f"/projects/{project_id}.json")
        
        # Get task counts - all tasks for this project
        # Note: meta.page.count is the total count across all pages, not page count
        # per Teamwork API v3 docs: https://apidocs.teamwork.com/guides/teamwork/how-does-paging-work
        all_tasks = self._request(
            "GET", 
            "/tasks.json", 
            params={"projectId": project_id, "pageSize": 1}
        )
        total_count = all_tasks.get("meta", {}).get("page", {}).get("count", 0)
        
        # Get overdue tasks count
        overdue_tasks = self._request(
            "GET",
            "/tasks.json",
            params={"projectId": project_id, "filter": "overdue", "pageSize": 1}
        )
        overdue_count = overdue_tasks.get("meta", {}).get("page", {}).get("count", 0)
        
        # Get tasks due this week
        thisweek_tasks = self._request(
            "GET",
            "/tasks.json",
            params={"projectId": project_id, "filter": "thisweek", "pageSize": 1}
        )
        thisweek_count = thisweek_tasks.get("meta", {}).get("page", {}).get("count", 0)
        
        # Health indicator: at-risk if >=10% tasks are overdue, or 3+ overdue tasks
        if total_count == 0:
            health = "on-track"  # No tasks = healthy
        else:
            overdue_pct = (overdue_count / total_count) * 100
            health = "at-risk" if overdue_pct >= 10 or overdue_count >= 3 else "on-track"
        
        # Build summary
        project_data = project.get("project", {})
        description = project_data.get("description", "") or ""
        if len(description) > 200:
            description = description[:197] + "..."  # Truncate with ellipsis
        return {
            "project": {
                "id": project_data.get("id"),
                "name": project_data.get("name"),
                "status": project_data.get("status"),
                "description": description,
            },
            "taskStats": {
                "total": total_count,
                "overdue": overdue_count,
                "dueThisWeek": thisweek_count,
            },
            "health": health,
        }

    # ===== Task Lists =====
    
    def list_task_lists(
        self,
        project_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """List task lists for a project."""
        return self._request(
            "GET",
            f"/projects/{project_id}/tasklists.json",
            params={"page": page, "pageSize": page_size}
        )
    
    def create_task_list(
        self,
        project_id: str,
        name: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new task list in a project.
        
        Note: Uses v1 API endpoint with 'todo-list' payload key per Teamwork SDK.
        v3 API doesn't fully support task list creation.
        """
        payload = {"todo-list": {"name": name}}
        if description:
            payload["todo-list"]["description"] = description
        return self._request_v1(
            "POST",
            f"/projects/{project_id}/tasklists.json",
            json_data=payload
        )
    
    # ===== Comments =====
    
    def list_task_comments(
        self,
        task_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """List comments on a task."""
        return self._request(
            "GET",
            f"/tasks/{task_id}/comments.json",
            params={"page": page, "pageSize": page_size}
        )
    
    def add_task_comment(
        self,
        task_id: str,
        body: str,
    ) -> Dict[str, Any]:
        """Add a comment to a task."""
        payload = {"comment": {"body": body}}
        return self._request(
            "POST",
            f"/tasks/{task_id}/comments.json",
            json_data=payload
        )
    
    # ===== Tags =====
    
    def list_tags(
        self,
        page: int = 1,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """List all available tags."""
        return self._request(
            "GET",
            "/tags.json",
            params={"page": page, "pageSize": page_size}
        )
    
    def add_tag_to_task(
        self,
        task_id: str,
        tag_ids: List[str],
    ) -> Dict[str, Any]:
        """Add tags to a task."""
        payload = {"tagIds": tag_ids}
        return self._request(
            "PUT",
            f"/tasks/{task_id}/tags.json",
            json_data=payload
        )
    
    # ===== Milestones =====
    
    def list_milestones(
        self,
        project_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """List milestones for a project."""
        return self._request(
            "GET",
            f"/projects/{project_id}/milestones.json",
            params={"page": page, "pageSize": page_size}
        )
    
    def get_milestone(self, milestone_id: str) -> Dict[str, Any]:
        """Get milestone details."""
        return self._request("GET", f"/milestones/{milestone_id}.json")
    
    # ===== Subtasks =====
    
    def list_subtasks(
        self,
        task_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """List subtasks of a task."""
        return self._request(
            "GET",
            f"/tasks/{task_id}/subtasks.json",
            params={"page": page, "pageSize": page_size}
        )
    
    def create_subtask(
        self,
        task_id: str,
        name: str,
        description: Optional[str] = None,
        assignee_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a subtask under a parent task."""
        payload = {"task": {"name": name, "parentTaskId": task_id}}
        if description:
            payload["task"]["description"] = description
        if assignee_ids:
            payload["task"]["assigneeIds"] = assignee_ids
        return self._request("POST", "/tasks.json", json_data=payload)
    
    # ===== Notebooks =====
    
    def list_notebooks(
        self,
        project_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """List notebooks for a project.
        
        Note: V3 API uses global /notebooks.json with projectIds filter.
        """
        return self._request(
            "GET",
            "/notebooks.json",
            params={"projectIds": project_id, "page": page, "pageSize": page_size}
        )
    
    def get_notebook(self, notebook_id: str) -> Dict[str, Any]:
        """Get notebook details."""
        return self._request("GET", f"/notebooks/{notebook_id}.json")
    
    # ===== Project Links =====
    # NOTE: Links endpoints are NOT available in Teamwork API v3.
    # These methods are commented out pending v1/v2 API integration.
    
    # def list_project_links(
    #     self,
    #     project_id: str,
    #     page: int = 1,
    #     page_size: int = 50,
    # ) -> Dict[str, Any]:
    #     """List links in a project. (NOT AVAILABLE IN V3)"""
    #     pass
    # 
    # def create_project_link(
    #     self,
    #     project_id: str,
    #     title: str,
    #     url: str,
    #     category_id: Optional[str] = None,
    #     description: Optional[str] = None,
    # ) -> Dict[str, Any]:
    #     """Create a link in a project. (NOT AVAILABLE IN V3)"""
    #     pass
    
    # ===== Project Operations =====
    
    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing project.
        
        Raises:
            ValueError: If no update fields are provided.
        """
        if all(v is None for v in [name, description, status, start_date, end_date]):
            raise ValueError("update_project requires at least one field to update")
        payload = {"project": {}}
        if name is not None:
            payload["project"]["name"] = name
        if description is not None:
            payload["project"]["description"] = description
        if status is not None:
            payload["project"]["status"] = status
        if start_date is not None:
            payload["project"]["startDate"] = start_date
        if end_date is not None:
            payload["project"]["endDate"] = end_date
        return self._request("PATCH", f"/projects/{project_id}.json", json_data=payload)
    
    def archive_project(self, project_id: str) -> Dict[str, Any]:
        """Archive a project."""
        return self.update_project(project_id, status="archived")
    
    # ===== Task List Operations =====
    
    def update_task_list(
        self,
        tasklist_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a task list.
        
        Note: Uses v1 API endpoint with 'todo-list' payload key per Teamwork SDK.
        
        Raises:
            ValueError: If neither name nor description is provided.
        """
        if name is None and description is None:
            raise ValueError("update_task_list requires at least one of 'name' or 'description'")
        payload = {"todo-list": {}}
        if name is not None:
            payload["todo-list"]["name"] = name
        if description is not None:
            payload["todo-list"]["description"] = description
        return self._request_v1("PUT", f"/tasklists/{tasklist_id}.json", json_data=payload)
    
    def move_task(
        self,
        task_id: str,
        target_tasklist_id: str,
        target_project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Move a task to a different task list or project.
        
        Note: Uses camelCase field names (taskListId, projectId) as expected by Teamwork API.
        """
        payload = {"task": {"taskListId": target_tasklist_id}}
        if target_project_id:
            payload["task"]["projectId"] = target_project_id
        return self._request("PATCH", f"/tasks/{task_id}.json", json_data=payload)
    
    # ===== Messages =====
    
    def list_messages(
        self,
        project_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """List messages (posts) for a project.
        
        Note: V3 API uses global /messages.json with projectIds filter.
        """
        return self._request(
            "GET",
            "/messages.json",
            params={"projectIds": project_id, "page": page, "pageSize": page_size}
        )
    
    def create_message(
        self,
        project_id: str,
        title: str,
        body: str,
        category_id: Optional[str] = None,
        notify: bool = False,
    ) -> Dict[str, Any]:
        """Create a new message (post) in a project."""
        payload = {
            "post": {
                "title": title,
                "body": body,
                "notify": notify,
            }
        }
        if category_id:
            payload["post"]["categoryId"] = category_id
        return self._request(
            "POST",
            f"/projects/{project_id}/posts.json",
            json_data=payload
        )

    # ===== Timers =====
    
    def get_active_timer(self) -> Dict[str, Any]:
        """Get the current user's active timer.
        
        Returns:
            Dictionary containing active timer details, or empty if no timer running
        """
        return self._request("GET", "/me/timers.json")
    
    def start_timer(
        self,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        description: Optional[str] = None,
        is_billable: bool = True,
    ) -> Dict[str, Any]:
        """Start a new timer.
        
        Uses V3 API endpoint: POST /me/timers.json
        Per official Teamwork API examples:
        https://github.com/Teamwork/Teamwork.com-API-Request-Examples
        
        Args:
            project_id: Project ID to track time against
            task_id: Optional task ID to track time against (0 or omit if not linked to task)
            description: Description of the work being done
            is_billable: Whether the time is billable (default: True)
            
        Returns:
            Dictionary containing started timer details
            
        Note:
            Only one timer can be active per task. If starting a project-level timer
            (no task_id), only one project-level timer can be active at a time.
        """
        # V3 API uses nested "timer" payload
        timer_data: Dict[str, Any] = {}
        if project_id:
            timer_data["projectId"] = int(project_id)
        if task_id:
            timer_data["taskId"] = int(task_id)
        if description:
            timer_data["description"] = description
        if not is_billable:
            timer_data["isBillable"] = False
            
        payload = {"timer": timer_data}
        return self._request("POST", "/me/timers.json", json_data=payload)
    
    def stop_timer(
        self,
        timer_id: str,
        description: Optional[str] = None,
        is_billable: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Stop a running timer and log the time.
        
        Args:
            timer_id: Timer ID to stop
            description: Optional updated description
            is_billable: Optional billable status update
            
        Returns:
            Dictionary containing completed timer and time entry details
        """
        payload: Dict[str, Any] = {"timer": {}}
        if description is not None:
            payload["timer"]["description"] = description
        if is_billable is not None:
            payload["timer"]["isBillable"] = is_billable
        return self._request("PUT", f"/me/timers/{timer_id}/complete.json", json_data=payload)
    
    def pause_timer(self, timer_id: str) -> Dict[str, Any]:
        """Pause a running timer.
        
        Args:
            timer_id: Timer ID to pause
        
        Returns:
            Dictionary containing paused timer details
        """
        return self._request("PUT", f"/me/timers/{timer_id}/pause.json")
    
    def resume_timer(self, timer_id: str) -> Dict[str, Any]:
        """Resume a paused timer.
        
        Args:
            timer_id: Timer ID to resume
        
        Returns:
            Dictionary containing resumed timer details
        """
        return self._request("PUT", f"/me/timers/{timer_id}/resume.json")
    
    def cancel_timer(self, timer_id: str) -> Dict[str, Any]:
        """Cancel a timer without logging time.
        
        Args:
            timer_id: Timer ID to cancel
        
        Returns:
            Dictionary containing the cancellation response
        """
        return self._request("DELETE", f"/me/timers/{timer_id}.json")
