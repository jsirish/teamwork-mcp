"""Teamwork MCP Server - Gateway-Centric Architecture.

This server provides Teamwork.com integration tools for the MCP Gateway.
It expects the gateway to handle OAuth authentication and pass bearer tokens
via the Authorization header.
"""

import logging
import os
from typing import Optional

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
    def teamwork_list_projects(
        page: int = 1,
        page_size: int = 50,
        _headers: dict = None,
    ) -> dict:
        """List all Teamwork projects.
        
        Args:
            page: Page number for pagination (default: 1)
            page_size: Number of results per page (default: 50, max: 500)
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing projects list and metadata
        """
        client = get_teamwork_client(_headers or {})
        return client.list_projects(page=page, page_size=page_size)
    
    
    @mcp.tool()
    def teamwork_get_project(
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
    def teamwork_create_project(
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
    # Task Tools
    # ========================================
    
    @mcp.tool()
    def teamwork_list_tasks(
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
    def teamwork_get_task(
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
    def teamwork_create_task(
        project_id: str,
        name: str,
        description: Optional[str] = None,
       due_date: Optional[str] = None,
        assignee_id: Optional[str] = None,
        _headers: dict = None,
    ) -> dict:
        """Create a new Teamwork task.
        
        Args:
            project_id: ID of the project to create the task in
            name: Task name
            description: Optional task description
            due_date: Optional due date (YYYY-MM-DD format)
            assignee_id: Optional ID of the person to assign the task to
            _headers: Request headers (automatically injected by gateway)
        
        Returns:
            Dictionary containing created task details
        """
        client = get_teamwork_client(_headers or {})
        return client.create_task(
            project_id=project_id,
            name=name,
            description=description,
            due_date=due_date,
            assignee_id=assignee_id,
        )
    
    
    @mcp.tool()
    def teamwork_update_task(
        task_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        due_date: Optional[str] = None,
        status: Optional[str] = None,
        _headers: dict = None,
    ) -> dict:
        """Update a Teamwork task.
        
        Args:
            task_id: ID of the task to update
            name: Optional new task name
            description: Optional new task description
            due_date: Optional new due date (YYYY-MM-DD format)
            status: Optional new status (e.g., "new", "in-progress", "completed")
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
            status=status,
        )
    
    
    @mcp.tool()
    def teamwork_complete_task(
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
    def teamwork_log_time(
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
    def teamwork_get_time_entries(
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
    def teamwork_list_people(
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
    def teamwork_get_me(
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
    
    LOGGER.info("✅ Teamwork tools registered")
    
    return mcp, settings


if __name__ == "__main__":
    """Run the Teamwork MCP server."""
    mcp, settings = create_app()
    run_server(mcp, settings)
