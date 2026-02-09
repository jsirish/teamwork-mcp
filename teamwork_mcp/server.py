"""Teamwork MCP Server - Gateway-Centric Architecture.

This server provides Teamwork.com integration tools for the MCP Gateway.
It expects the gateway to handle OAuth authentication and pass bearer tokens
via the Authorization header.
"""

import logging
import os
from typing import List, Optional

from pydantic import Field
from fastmcp import FastMCP

from mcp_base import (
    create_base_app,
    BaseMCPSettings,
    run_server,
    extract_token_from_headers,
)

from .client import TeamworkClient

# Configure logging
LOGGER = logging.getLogger(__name__)

# Environment variables
DEFAULT_DOMAIN = os.getenv("TEAMWORK_DOMAIN", "")


class TeamworkSettings(BaseMCPSettings):
    """Teamwork-specific settings extending the base MCP settings."""
    
    # Override defaults for Teamwork
    name: str = Field(default="teamwork-mcp")
    version: str = Field(default="1.0.0")
    description: str = Field(default="Teamwork.com project management tools")
    port: int = Field(default=3005)


def get_teamwork_client(headers: dict) -> TeamworkClient:
    """Create an authenticated Teamwork client from request headers.
    
    Uses mcp_base.extract_token_from_headers() to extract the bearer token
    from the _headers dict injected by the gateway.
    
    Args:
        headers: Request headers dict containing Authorization and optionally X-Teamwork-Domain
        
    Returns:
        Authenticated TeamworkClient instance
    """
    headers = headers or {}
    access_token = extract_token_from_headers(headers)
    if not access_token:
        raise ValueError("Missing Authorization header. This server requires OAuth authentication via the gateway.")
    
    domain = headers.get("x-teamwork-domain") or DEFAULT_DOMAIN
    
    if not domain:
        raise ValueError(
            "Teamwork installation domain is required. "
            "Provide via X-Teamwork-Domain header or TEAMWORK_DOMAIN environment variable."
        )
    
    return TeamworkClient(access_token=access_token, installation_domain=domain)


def create_app():
    """Create the Teamwork MCP server."""
    settings = TeamworkSettings()
    mcp = create_base_app(settings)
    
    LOGGER.info("📦 Registering Teamwork tools...")
    
    # ========================================
    # Project Tools
    # ========================================
    
    @mcp.tool()
    def list_projects(
        page: int = 1,
        page_size: int = 25,
        include_details: bool = False,
        _headers: dict = None,
    ) -> dict:
        """List all Teamwork projects.
        
        By default, returns minimal project data (id, name, status, company) to reduce
        response size for AI clients. Use include_details=True for full project objects.
        
        Args:
            page: Page number for pagination (default: 1)
            page_size: Number of results per page (default: 25, max: 500)
            include_details: Return full project objects (default: False for minimal data)
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing projects list and pagination metadata
        """
        client = get_teamwork_client(_headers or {})
        return client.list_projects(page=page, page_size=page_size, include_details=include_details)

    
    
    @mcp.tool()
    def get_project(
        project_id: str,
        _headers: dict = None,
    ) -> dict:
        """Get details of a specific Teamwork project.
        
        Args:
            project_id: The ID of the project to retrieve
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing project details
        """
        client = get_teamwork_client(_headers or {})
        return client.get_project(project_id)
    
    
    @mcp.tool()
    def get_project_budget(
        budget_id: str,
        _headers: dict = None,
    ) -> dict:
        """Get detailed budget information for a project budget.
        
        Use the budget ID from financialBudget.id or timeBudget.id
        returned by teamwork_list_projects or teamwork_get_project.
        
        Args:
            budget_id: The budget ID (e.g., "127645" from financialBudget.id)
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing budget details including:
            - capacity: Total budget amount (hours or currency)
            - capacityUsed: Amount used so far
            - status: Budget status
            - type: "FINANCIAL" or "TIME"
            - currencyCode: Currency for financial budgets
        """
        client = get_teamwork_client(_headers or {})
        return client.get_project_budget(budget_id)
    
    
    @mcp.tool()
    def list_project_budgets(
        project_id: str,
        _headers: dict = None,
    ) -> dict:
        """List all budgets for a Teamwork project.
        
        Returns both time and financial budgets with full details including
        capacity, capacityUsed, status, and other budget information.
        
        Args:
            project_id: The project ID to get budgets for
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing:
            - project_id: The project ID
            - project_name: The project name
            - budgets: List of budget objects with full details
            - has_time_budget: Whether project has a time budget
            - has_financial_budget: Whether project has a financial budget
        """
        client = get_teamwork_client(_headers or {})
        return client.list_project_budgets(project_id)
    
    
    @mcp.tool()
    def create_project(
        name: str,
        description: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        _headers: dict = None,
    ) -> dict:
        """Create a new Teamwork project.
        
        Args:
            name: Project name
            description: Optional project description
            start_date: Optional start date (YYYY-MM-DD format)
            end_date: Optional end date (YYYY-MM-DD format)
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing created project details
        """
        client = get_teamwork_client(_headers or {})
        return client.create_project(
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
        )
    
    
    # ========================================
    # Time Totals / Unofficial Budgets  
    # ========================================
    
    @mcp.tool()
    def get_project_time_totals(
        project_id: str,
        _headers: dict = None,
    ) -> dict:
        """Get time totals for a project (unofficial budget).
        
        Fetches aggregated estimated and logged time for an entire project.
        Useful for "unofficial budgets" where total task estimates serve as
        the budget and logged time represents usage.
        
        Args:
            project_id: Project ID to get time totals for
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing:
            - project_id: The project ID
            - estimated_minutes: Total estimated time (budget)
            - minutes: Total logged time (used)
            - remaining_minutes: Difference (budget - used)
            - is_over_budget: True if logged exceeds estimated
        """
        client = get_teamwork_client(_headers or {})
        return client.get_project_time_totals(project_id)
    
    
    @mcp.tool()
    def get_tasklist_time_totals(
        tasklist_id: str,
        _headers: dict = None,
    ) -> dict:
        """Get time totals for a tasklist.
        
        Fetches aggregated estimated and logged time for tasks in a tasklist.
        
        Args:
            tasklist_id: Tasklist ID to get time totals for
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing:
            - tasklist_id: The tasklist ID
            - estimated_minutes: Total estimated time
            - minutes: Total logged time
            - remaining_minutes: Difference
            - is_over_budget: True if logged exceeds estimated
        """
        client = get_teamwork_client(_headers or {})
        return client.get_tasklist_time_totals(tasklist_id)
    
    
    @mcp.tool()
    def get_task_time_totals(
        task_id: str,
        _headers: dict = None,
    ) -> dict:
        """Get time totals for a specific task.
        
        Fetches estimated and logged time for a single task.
        
        Args:
            task_id: Task ID to get time totals for
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing:
            - task_id: The task ID
            - estimated_minutes: Estimated time for the task
            - minutes: Logged time on the task
            - remaining_minutes: Difference
            - is_over_budget: True if logged exceeds estimated
        """
        client = get_teamwork_client(_headers or {})
        return client.get_task_time_totals(task_id)
    
    
    @mcp.tool()
    def estimate_project_budget(
        project_id: str,
        _headers: dict = None,
    ) -> dict:
        """Get unofficial budget estimate for a project.
        
        High-level tool that returns budget-like data calculated from
        task estimated times and logged hours. Ideal for projects without
        official Teamwork budgets (limited to 30 on Grow tier).
        
        Args:
            project_id: Project ID to estimate budget for
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing:
            - project_id: The project ID
            - project_name: Project name
            - budget_type: "estimated" (indicates unofficial/calculated)
            - budget_minutes: Total estimated time (the "budget")
            - used_minutes: Total logged time
            - remaining_minutes: Difference
            - percent_used: Usage percentage (None if no estimate but time logged)
            - is_over_budget: True if over budget
            - has_official_budget: True if project has a Teamwork budget
        """
        client = get_teamwork_client(_headers or {})
        return client.estimate_project_budget(project_id)
    
    
    # ========================================
    # Task Tools
    # ========================================
    
    @mcp.tool()
    def list_tasks(
        project_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        _headers: dict = None,
    ) -> dict:
        """List Teamwork tasks, optionally filtered by project.
        
        Args:
            project_id: Optional project ID to filter tasks
            page: Page number for pagination (default: 1)
            page_size: Number of results per page (default: 50, max: 500)
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing tasks list and metadata
        """
        client = get_teamwork_client(_headers or {})
        return client.list_tasks(project_id=project_id, page=page, page_size=page_size)
    
    
    @mcp.tool()
    def get_task(
        task_id: str,
        _headers: dict = None,
    ) -> dict:
        """Get details of a specific Teamwork task.
        
        Args:
            task_id: The ID of the task to retrieve
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing task details
        """
        client = get_teamwork_client(_headers or {})
        return client.get_task(task_id)
    
    
    @mcp.tool()
    def create_teamwork_task(
        tasklist_id: str,
        name: str,
        description: Optional[str] = None,
        due_date: Optional[str] = None,
        assignee_ids: Optional[List[str]] = None,
        priority: Optional[str] = None,
        estimated_minutes: Optional[int] = None,
        progress: Optional[int] = None,
        _headers: dict = None,
    ) -> dict:
        """Create a new task in Teamwork.
        
        Note:
            This tool replaces the older ``create_task`` tool exposed by the
            gateway. The previous ``create_task`` tool name collided with HubSpot's
            tool of the same name. Clients currently calling ``create_task`` should
            migrate to ``create_teamwork_task`` to ensure forward compatibility.
        
        Args:
            tasklist_id: ID of the task list to create the task in
            name: Task name
            description: Optional task description
            due_date: Optional due date (YYYY-MM-DD format)
            assignee_ids: Optional list of user IDs to assign the task to
            priority: Optional priority (low, medium, high)
            estimated_minutes: Optional estimated time to complete in minutes
            progress: Optional initial progress percentage (0-100)
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing created task details
        """
        client = get_teamwork_client(_headers or {})
        return client.create_task(
            name=name,
            tasklist_id=tasklist_id,
            description=description,
            due_date=due_date,
            assignee_ids=assignee_ids,
            priority=priority,
            estimated_minutes=estimated_minutes,
            progress=progress,
        )
    
    
    @mcp.tool()
    def update_task(
        task_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        due_date: Optional[str] = None,
        priority: Optional[str] = None,
        completed: Optional[bool] = None,
        estimated_minutes: Optional[int] = None,
        progress: Optional[int] = None,
        _headers: dict = None,
    ) -> dict:
        """Update a Teamwork task.
        
        Args:
            task_id: ID of the task to update
            name: Optional new task name
            description: Optional new task description
            due_date: Optional new due date (YYYY-MM-DD format)
            priority: Optional priority (low, medium, high)
            completed: Optional completion status (true/false)
            estimated_minutes: Optional estimated time to complete in minutes
            progress: Optional progress percentage (0-100)
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing update confirmation
        """
        client = get_teamwork_client(_headers or {})
        return client.update_task(
            task_id=task_id,
            name=name,
            description=description,
            due_date=due_date,
            priority=priority,
            completed=completed,
            estimated_minutes=estimated_minutes,
            progress=progress,
        )
    
    
    @mcp.tool()
    def complete_task(
        task_id: str,
        _headers: dict = None,
    ) -> dict:
        """Mark a Teamwork task as complete.
        
        Args:
            task_id: ID of the task to complete
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing completion confirmation
        """
        client = get_teamwork_client(_headers or {})
        return client.complete_task(task_id)
    
    
    # ========================================
    # Time Tracking Tools
    # ========================================
    
    @mcp.tool()
    def log_time(
        project_id: str,
        hours: float,
        description: str,
        date: Optional[str] = None,
        task_id: Optional[str] = None,
        _headers: dict = None,
    ) -> dict:
        """Log time to a Teamwork project or task.
        
        Args:
            project_id: ID of the project to log time to
            hours: Number of hours to log (can be decimal, e.g., 1.5)
            description: Description of the work performed
            date: Optional date for the time entry (YYYY-MM-DD format, defaults to today)
            task_id: Optional ID of the task to log time to
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing time entry details
        """
        client = get_teamwork_client(_headers or {})
        return client.log_time(
            project_id=project_id,
            hours=hours,
            description=description,
            date=date,
            task_id=task_id,
        )
    
    
    @mcp.tool()
    def get_time_entries(
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        _headers: dict = None,
    ) -> dict:
        """Get time entries from Teamwork.
        
        Args:
            project_id: Optional project ID to filter time entries
            user_id: Optional user ID to filter time entries
            page: Page number for pagination (default: 1)
            page_size: Number of results per page (default: 50, max: 500)
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing time entries list and metadata
        """
        client = get_teamwork_client(_headers or {})
        return client.get_time_entries(
            project_id=project_id,
            user_id=user_id,
            page=page,
            page_size=page_size,
        )
    
    
    # ========================================
    # People Tools
    # ========================================
    
    @mcp.tool()
    def list_people(
        page: int = 1,
        page_size: int = 50,
        _headers: dict = None,
    ) -> dict:
        """List all people in the Teamwork account.
        
        Args:
            page: Page number for pagination (default: 1)
            page_size: Number of results per page (default: 50, max: 500)
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing people list and metadata
        """
        client = get_teamwork_client(_headers or {})
        return client.list_people(page=page, page_size=page_size)
    
    
    @mcp.tool()
    def get_me(
        _headers: dict = None,
    ) -> dict:
        """Get current authenticated user's information.
        
        Args:
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing current user details
        """
        client = get_teamwork_client(_headers or {})
        return client.get_me()
    
    # ========================================
    # Planning Tools (New)
    # ========================================
    
    @mcp.tool()
    def get_my_tasks(
        date_filter: str = "within7",
        include_completed: bool = False,
        _headers: dict = None,
    ) -> dict:
        """Get tasks assigned to the current user with due date filtering.
        
        Args:
            date_filter: overdue, today, thisweek, within7, within14, within30
            include_completed: Whether to include completed tasks
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing filtered tasks for planning
        """
        client = get_teamwork_client(_headers or {})
        me = client.get_me()
        user_id = me.get("person", {}).get("id") or me.get("id")
        return client.get_my_tasks(str(user_id), date_filter, include_completed)
    
    
    @mcp.tool()
    def get_project_summary(
        project_id: str,
        _headers: dict = None,
    ) -> dict:
        """Get a project health summary with task statistics.
        
        Args:
            project_id: Project ID to summarize
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary with project info, task stats, and health status
        """
        client = get_teamwork_client(_headers or {})
        return client.get_project_summary(project_id)
    
    
    # ========================================
    # Task List Tools (New)
    # ========================================
    
    @mcp.tool()
    def list_task_lists(
        project_id: str,
        page: int = 1,
        page_size: int = 50,
        _headers: dict = None,
    ) -> dict:
        """List task lists for a project.
        
        Args:
            project_id: Project ID
            page: Page number
            page_size: Results per page
            _headers: Request headers (automatically injected by gateway)
        """
        client = get_teamwork_client(_headers or {})
        return client.list_task_lists(project_id, page, page_size)
    
    
    @mcp.tool()
    def create_task_list(
        project_id: str,
        name: str,
        description: Optional[str] = None,
        _headers: dict = None,
    ) -> dict:
        """Create a new task list in a project.
        
        Args:
            project_id: Project ID
            name: Task list name
            description: Optional description
            _headers: Request headers (automatically injected by gateway)
        """
        client = get_teamwork_client(_headers or {})
        return client.create_task_list(project_id, name, description)
    
    
    @mcp.tool()
    def update_task_list(
        tasklist_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        _headers: dict = None,
    ) -> dict:
        """Update an existing task list.
        
        Args:
            tasklist_id: Task list ID to update
            name: New name for the task list
            description: New description for the task list
            _headers: Request headers (automatically injected by gateway)
        """
        client = get_teamwork_client(_headers or {})
        return client.update_task_list(tasklist_id, name, description)
    
    
    # ========================================
    # Comment Tools (New)
    # ========================================
    
    @mcp.tool()
    def list_task_comments(
        task_id: str,
        page: int = 1,
        page_size: int = 50,
        _headers: dict = None,
    ) -> dict:
        """List comments on a task.
        
        Args:
            task_id: Task ID
            page: Page number
            page_size: Results per page
            _headers: Request headers (automatically injected by gateway)
        """
        client = get_teamwork_client(_headers or {})
        return client.list_task_comments(task_id, page, page_size)
    
    
    @mcp.tool()
    def add_task_comment(
        task_id: str,
        body: str,
        _headers: dict = None,
    ) -> dict:
        """Add a comment to a task.
        
        Args:
            task_id: Task ID
            body: Comment text
            _headers: Request headers (automatically injected by gateway)
        """
        client = get_teamwork_client(_headers or {})
        return client.add_task_comment(task_id, body)
    
    
    # ========================================
    # Tag Tools (New)
    # ========================================
    
    @mcp.tool()
    def list_tags(
        page: int = 1,
        page_size: int = 100,
        _headers: dict = None,
    ) -> dict:
        """List all available tags.
        
        Args:
            page: Page number
            page_size: Results per page
            _headers: Request headers (automatically injected by gateway)
        """
        client = get_teamwork_client(_headers or {})
        return client.list_tags(page, page_size)
    
    
    @mcp.tool()
    def add_tag_to_task(
        task_id: str,
        tag_ids: List[str],
        _headers: dict = None,
    ) -> dict:
        """Add tags to a task.
        
        Args:
            task_id: Task ID
            tag_ids: List of tag IDs to add
            _headers: Request headers (automatically injected by gateway)
        """
        client = get_teamwork_client(_headers or {})
        return client.add_tag_to_task(task_id, tag_ids)
    
    
    # ========================================
    # Milestone Tools (New)
    # ========================================
    
    @mcp.tool()
    def list_milestones(
        project_id: str,
        page: int = 1,
        page_size: int = 50,
        _headers: dict = None,
    ) -> dict:
        """List milestones for a project.
        
        Args:
            project_id: Project ID
            page: Page number
            page_size: Results per page
            _headers: Request headers (automatically injected by gateway)
        """
        client = get_teamwork_client(_headers or {})
        return client.list_milestones(project_id, page, page_size)
    
    
    @mcp.tool()
    def get_milestone(
        milestone_id: str,
        _headers: dict = None,
    ) -> dict:
        """Get milestone details.
        
        Args:
            milestone_id: Milestone ID
            _headers: Request headers (automatically injected by gateway)
        """
        client = get_teamwork_client(_headers or {})
        return client.get_milestone(milestone_id)
    
    
    # ========================================
    # Subtask Tools (New)
    # ========================================
    
    @mcp.tool()
    def list_subtasks(
        task_id: str,
        page: int = 1,
        page_size: int = 50,
        _headers: dict = None,
    ) -> dict:
        """List subtasks of a task.
        
        Args:
            task_id: Task ID
            page: Page number
            page_size: Results per page
            _headers: Request headers (automatically injected by gateway)
        """
        client = get_teamwork_client(_headers or {})
        return client.list_subtasks(task_id, page, page_size)
    
    
    @mcp.tool()
    def create_subtask(
        task_id: str,
        name: str,
        description: Optional[str] = None,
        assignee_ids: Optional[List[str]] = None,
        _headers: dict = None,
    ) -> dict:
        """Create a subtask under a parent task.
        
        Args:
            task_id: Parent task ID
            name: Subtask name
            description: Optional description
            assignee_ids: Optional list of user IDs to assign the subtask to
            _headers: Request headers (automatically injected by gateway)
        """
        client = get_teamwork_client(_headers or {})
        return client.create_subtask(task_id, name, description, assignee_ids)
    
    
    # ========================================
    # Notebook Tools (New)
    # ========================================
    
    @mcp.tool()
    def list_notebooks(
        project_id: str,
        page: int = 1,
        page_size: int = 50,
        _headers: dict = None,
    ) -> dict:
        """List notebooks for a project.
        
        Args:
            project_id: Project ID
            page: Page number
            page_size: Results per page
            _headers: Request headers (automatically injected by gateway)
        """
        client = get_teamwork_client(_headers or {})
        return client.list_notebooks(project_id, page, page_size)
    
    
    @mcp.tool()
    def get_notebook(
        notebook_id: str,
        _headers: dict = None,
    ) -> dict:
        """Get notebook details.
        
        Args:
            notebook_id: Notebook ID
            _headers: Request headers (automatically injected by gateway)
        """
        client = get_teamwork_client(_headers or {})
        return client.get_notebook(notebook_id)
    
    
    # Project Link Tools
    # NOTE: Project Links are planned features mentioned in user requirements,
    # but they are NOT available in the Teamwork API v3 due to API limitations.
    # These tools remain commented out pending v1/v2 (or other compatible) API
    # integration that exposes Project Links.
    # ========================================
    
    # @mcp.tool()
    # def list_project_links(
    #     project_id: str,
    #     page: int = 1,
    #     page_size: int = 50,
    #     _headers: dict = None,
    # ) -> dict:
    #     """List links in a project. (NOT AVAILABLE IN V3)"""
    #     client = get_teamwork_client(_headers or {})
    #     return client.list_project_links(project_id, page, page_size)
    # 
    # @mcp.tool()
    # def create_project_link(
    #     project_id: str,
    #     title: str,
    #     url: str,
    #     description: Optional[str] = None,
    #     _headers: dict = None,
    # ) -> dict:
    #     """Create a link in a project. (NOT AVAILABLE IN V3)"""
    #     client = get_teamwork_client(_headers or {})
    #     return client.create_project_link(project_id, title, url, description=description)
    
    
    # ========================================
    # Project Operations (New)
    # ========================================
    
    @mcp.tool()
    def update_project(
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        _headers: dict = None,
    ) -> dict:
        """Update an existing project.
        
        Args:
            project_id: Project ID
            name: New name
            description: New description
            status: New status (e.g., active, archived)
            start_date: Project start date (YYYY-MM-DD format)
            end_date: Project end date (YYYY-MM-DD format)
            _headers: Request headers (automatically injected by gateway)
        """
        client = get_teamwork_client(_headers or {})
        return client.update_project(project_id, name, description, status, start_date, end_date)
    
    
    @mcp.tool()
    def archive_project(
        project_id: str,
        _headers: dict = None,
    ) -> dict:
        """Archive a project.
        
        Args:
            project_id: Project ID
            _headers: Request headers (automatically injected by gateway)
        """
        client = get_teamwork_client(_headers or {})
        return client.archive_project(project_id)
    
    
    # ========================================
    # Task Operations (New)
    # ========================================
    
    @mcp.tool()
    def move_task(
        task_id: str,
        target_tasklist_id: str,
        target_project_id: Optional[str] = None,
        _headers: dict = None,
    ) -> dict:
        """Move a task to a different task list or project.
        
        Args:
            task_id: Task ID to move
            target_tasklist_id: Destination task list ID
            target_project_id: Optional destination project ID
            _headers: Request headers (automatically injected by gateway)
        """
        client = get_teamwork_client(_headers or {})
        return client.move_task(task_id, target_tasklist_id, target_project_id)
    
    
    # ========================================
    # Message Tools (New)
    # ========================================
    
    @mcp.tool()
    def list_messages(
        project_id: str,
        page: int = 1,
        page_size: int = 50,
        _headers: dict = None,
    ) -> dict:
        """List messages (posts) for a project.
        
        Args:
            project_id: Project ID
            page: Page number
            page_size: Results per page
            _headers: Request headers (automatically injected by gateway)
        """
        client = get_teamwork_client(_headers or {})
        return client.list_messages(project_id, page, page_size)
    
    
    @mcp.tool()
    def create_message(
        project_id: str,
        title: str,
        body: str,
        notify: bool = False,
        category_id: Optional[str] = None,
        _headers: dict = None,
    ) -> dict:
        """Create a new message (post) in a project.
        
        Args:
            project_id: Project ID
            title: Message title
            body: Message body
            notify: Whether to notify project members
            category_id: Optional message category ID
            _headers: Request headers (automatically injected by gateway)
        """
        client = get_teamwork_client(_headers or {})
        return client.create_message(project_id, title, body, category_id=category_id, notify=notify)
    
    
    # ========================================
    # Timer Tools
    # ========================================
    
    @mcp.tool()
    def get_active_timer(
        _headers: dict = None,
    ) -> dict:
        """Get the current user's active timer.
        
        Args:
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing active timer details, or empty if no timer running
        """
        client = get_teamwork_client(_headers or {})
        return client.get_active_timer()
    
    
    @mcp.tool()
    def start_timer(
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        description: Optional[str] = None,
        is_billable: bool = True,
        _headers: dict = None,
    ) -> dict:
        """Start a new timer for time tracking.
        
        Args:
            project_id: Optional project ID to track time against
            task_id: Optional task ID to track time against
            description: Description of the work being done
            is_billable: Whether the time is billable (default: True)
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing started timer details
        """
        client = get_teamwork_client(_headers or {})
        return client.start_timer(
            project_id=project_id,
            task_id=task_id,
            description=description,
            is_billable=is_billable,
        )
    
    
    @mcp.tool()
    def stop_timer(
        timer_id: str,
        description: Optional[str] = None,
        is_billable: Optional[bool] = None,
        _headers: dict = None,
    ) -> dict:
        """Stop a running timer and log the time entry.
        
        Args:
            timer_id: Timer ID to stop (get from teamwork_get_active_timer)
            description: Optional updated description for the time entry
            is_billable: Optional billable status update
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing completed timer and created time entry
        """
        client = get_teamwork_client(_headers or {})
        return client.stop_timer(timer_id, description=description, is_billable=is_billable)
    
    
    @mcp.tool()
    def pause_timer(
        timer_id: str,
        _headers: dict = None,
    ) -> dict:
        """Pause a running timer.
        
        Args:
            timer_id: Timer ID to pause
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing the paused timer details
        """
        client = get_teamwork_client(_headers or {})
        return client.pause_timer(timer_id)
    
    
    @mcp.tool()
    def resume_timer(
        timer_id: str,
        _headers: dict = None,
    ) -> dict:
        """Resume a paused timer.
        
        Args:
            timer_id: Timer ID to resume
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing resumed timer details
        """
        client = get_teamwork_client(_headers or {})
        return client.resume_timer(timer_id)
    
    
    @mcp.tool()
    def cancel_timer(
        timer_id: str,
        _headers: dict = None,
    ) -> dict:
        """Cancel a timer without logging time.
        
        Use this to discard a timer that was started by mistake.
        
        Args:
            timer_id: Timer ID to cancel
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing the cancellation response
        """
        client = get_teamwork_client(_headers or {})
        return client.cancel_timer(timer_id)
    
    
    LOGGER.info("✅ Teamwork tools registered")
    
    return mcp, settings


if __name__ == "__main__":
    """Run the Teamwork MCP server."""
    mcp, settings = create_app()
    run_server(mcp, settings)
