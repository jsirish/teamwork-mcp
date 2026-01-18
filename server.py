"""Teamwork MCP Server.

Provides project management tools via Teamwork API v3.
All authentication is handled by the MCP Gateway via OAuth 2.0.
"""

import logging
import os
from typing import List, Optional

from pydantic import Field
from mcp_base import (
    create_base_app,
    BaseMCPSettings,
    run_server,
    extract_bearer_token,
    extract_header,
    AuthenticationError,
)

from teamwork_mcp.client import TeamworkClient

LOGGER = logging.getLogger(__name__)


class TeamworkSettings(BaseMCPSettings):
    """Settings for Teamwork MCP server."""
    
    name: str = Field(default="Teamwork")
    version: str = Field(default="0.1.0")
    port: int = Field(default=3005)


def create_app():
    """Create the Teamwork MCP server."""
    settings = TeamworkSettings()
    mcp = create_base_app(settings, register_health=True)
    
    # Register Teamwork tools
    _register_teamwork_tools(mcp, settings)
    
    return mcp, settings


def _get_client(ctx):
    """Get authenticated Teamwork client from context.
    
    Uses mcp_base utilities for consistent token and header extraction.
    The gateway injects the OAuth access token via the Authorization header
    and installation domain via the X-Teamwork-Domain header.
    """
    access_token = extract_bearer_token(ctx, fallback_env="TEAMWORK_ACCESS_TOKEN")
    installation_domain = extract_header(
        ctx,
        "X-Teamwork-Domain",
        fallback_env="TEAMWORK_DOMAIN",
        default="dynamic8.teamwork.com"
    )
    
    if not access_token:
        raise AuthenticationError(
            "No Teamwork access token available. "
            "Please authenticate via the gateway's OAuth flow at /oauth/teamwork/authorize"
        )
    
    return TeamworkClient(
        access_token=access_token,
        installation_domain=installation_domain
    )



def _register_teamwork_tools(mcp, settings):
    """Register Teamwork tools."""
    
    # ===== Project Management =====
    
    @mcp.tool()
    def teamwork_list_projects(
        ctx,
        page: int = Field(default=1, description="Page number"),
        page_size: int = Field(default=50, description="Results per page (max 100)"),
    ) -> dict:
        """List all Teamwork projects with pagination.
        
        Returns a list of projects you have access to, including project details
        like name, description, status, and dates.
        """
        client = _get_client(ctx)
        return client.list_projects(page=page, page_size=page_size)
    
    @mcp.tool()
    def teamwork_get_project(
        ctx,
        project_id: str = Field(..., description="Project ID"),
    ) -> dict:
        """Get detailed information about a specific Teamwork project.
        
        Returns full project details including name, description, status, dates,
        company info, and project settings.
        """
        client = _get_client(ctx)
        return client.get_project(project_id)
    
    @mcp.tool()
    def teamwork_create_project(
        ctx,
        name: str = Field(..., description="Project name"),
        description: Optional[str] = Field(default=None, description="Project description"),
        start_date: Optional[str] = Field(default=None, description="Start date (YYYY-MM-DD)"),
        end_date: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD)"),
    ) -> dict:
        """Create a new Teamwork project.
        
        Creates a new project with the specified name and optional details.
        Returns the created project information including the new project ID.
        """
        client = _get_client(ctx)
        return client.create_project(
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
        )
    
    # ===== Task Management =====
    
    @mcp.tool()
    def teamwork_list_tasks(
        ctx,
        project_id: Optional[str] = Field(default=None, description="Filter by project ID"),
        page: int = Field(default=1, description="Page number"),
        page_size: int = Field(default=50, description="Results per page (max 100)"),
    ) -> dict:
        """List tasks, optionally filtered by project.
        
        Returns a list of tasks with details like name, status, assignees, due dates,
        and priority. Can be filtered to show only tasks from a specific project.
        """
        client = _get_client(ctx)
        return client.list_tasks(
            project_id=project_id,
            page=page,
            page_size=page_size,
        )
    
    @mcp.tool()
    def teamwork_get_task(
        ctx,
        task_id: str = Field(..., description="Task ID"),
    ) -> dict:
        """Get detailed information about a specific task.
        
        Returns full task details including name, description, status, assignees,
        dates, comments, and related information.
        """
        client = _get_client(ctx)
        return client.get_task(task_id)
    
    @mcp.tool()
    def teamwork_create_task(
        ctx,
        name: str = Field(..., description="Task name"),
        tasklist_id: str = Field(..., description="Task list ID"),
        description: Optional[str] = Field(default=None, description="Task description"),
        due_date: Optional[str] = Field(default=None, description="Due date (YYYY-MM-DD)"),
        assignee_ids: Optional[List[str]] = Field(default=None, description="List of user IDs to assign"),
        priority: Optional[str] = Field(default=None, description="Priority (low, medium, high)"),
    ) -> dict:
        """Create a new task in a task list.
        
        Creates a new task with the specified name and optional details.
        Returns the created task information including the new task ID.
        """
        client = _get_client(ctx)
        return client.create_task(
            name=name,
            tasklist_id=tasklist_id,
            description=description,
            due_date=due_date,
            assignee_ids=assignee_ids,
            priority=priority,
        )
    
    @mcp.tool()
    def teamwork_update_task(
        ctx,
        task_id: str = Field(..., description="Task ID to update"),
        name: Optional[str] = Field(default=None, description="New task name"),
        description: Optional[str] = Field(default=None, description="New task description"),
        completed: Optional[bool] = Field(default=None, description="Mark as completed/incomplete"),
        due_date: Optional[str] = Field(default=None, description="New due date (YYYY-MM-DD)"),
        priority: Optional[str] = Field(default=None, description="New priority (low, medium, high)"),
    ) -> dict:
        """Update an existing task.
        
        Modifies task details. Only provided fields will be updated.
        Returns the updated task information.
        """
        client = _get_client(ctx)
        return client.update_task(
            task_id=task_id,
            name=name,
            description=description,
            completed=completed,
            due_date=due_date,
            priority=priority,
        )
    
    @mcp.tool()
    def teamwork_complete_task(
        ctx,
        task_id: str = Field(..., description="Task ID to mark as complete"),
    ) -> dict:
        """Mark a task as complete.
        
        A convenience method to quickly complete a task without specifying
        other update parameters.
        """
        client = _get_client(ctx)
        return client.complete_task(task_id)
    
    # ===== Time Tracking =====
    
    @mcp.tool()
    def teamwork_list_time_entries(
        ctx,
        project_id: Optional[str] = Field(default=None, description="Filter by project ID"),
        page: int = Field(default=1, description="Page number"),
        page_size: int = Field(default=50, description="Results per page (max 100)"),
    ) -> dict:
        """List time entries, optionally filtered by project.
        
        Returns logged time entries with details like hours, description, date,
        user, and associated project/task.
        """
        client = _get_client(ctx)
        return client.list_time_entries(
            project_id=project_id,
            page=page,
            page_size=page_size,
        )
    
    @mcp.tool()
    def teamwork_log_time(
        ctx,
        project_id: str = Field(..., description="Project ID"),
        hours: float = Field(..., description="Hours to log"),
        description: str = Field(..., description="Description of work"),
        date: Optional[str] = Field(default=None, description="Date (YYYY-MM-DD, defaults to today)"),
        task_id: Optional[str] = Field(default=None, description="Optional task ID"),
    ) -> dict:
        """Log time spent on a project or task.
        
        Creates a new time entry for tracking work. Can be associated with
        a specific task or logged at the project level.
        """
        client = _get_client(ctx)
        return client.log_time(
            project_id=project_id,
            hours=hours,
            description=description,
            date=date,
            task_id=task_id,
        )
    
    # ===== People Management =====
    
    @mcp.tool()
    def teamwork_list_people(
        ctx,
        project_id: Optional[str] = Field(default=None, description="Filter by project ID"),
    ) -> dict:
        """List people, optionally filtered by project.
        
        Returns a list of team members with details like name, email, role,
        and permissions. Can be filtered to show only people on a specific project.
        """
        client = _get_client(ctx)
        return client.list_people(project_id=project_id)
    
    @mcp.tool()
    def teamwork_get_me(ctx) -> dict:
        """Get current authenticated user information.
        
        Returns your Teamwork profile including user ID, name, email, company,
        and account permissions. Useful for getting your user ID for other operations.
        """
        client = _get_client(ctx)
        return client.get_me()
    
    LOGGER.info("✅ Teamwork tools registered (10 tools)")


if __name__ == "__main__":
    mcp, settings = create_app()
    run_server(mcp, settings)
