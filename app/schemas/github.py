"""Pydantic schemas for GitHub integration."""
from datetime import datetime
from pydantic import BaseModel, Field


class GitConnectionCreate(BaseModel):
    repo_owner: str = Field(min_length=1, max_length=200)
    repo_name: str = Field(min_length=1, max_length=200)
    default_branch: str = Field(default="main", max_length=100)
    auth_token: str = Field(min_length=1)
    webhook_secret: str | None = None
    polling_enabled: bool = True


class GitConnectionUpdate(BaseModel):
    repo_owner: str | None = Field(default=None, min_length=1, max_length=200)
    repo_name: str | None = Field(default=None, min_length=1, max_length=200)
    default_branch: str | None = Field(default=None, max_length=100)
    auth_token: str | None = Field(default=None, min_length=1)
    webhook_secret: str | None = None
    polling_enabled: bool | None = None


class GitConnectionResponse(BaseModel):
    id: str
    project_id: str
    repo_owner: str
    repo_name: str
    default_branch: str
    polling_enabled: bool
    last_synced_at: datetime | None = None
    created_at: datetime


class TestRunResponse(BaseModel):
    id: str
    project_id: str
    github_run_id: int
    branch: str
    commit_sha: str
    status: str
    conclusion: str | None = None
    total_tests: int | None = None
    passed: int | None = None
    failed: int | None = None
    skipped: int | None = None
    duration_seconds: float | None = None
    run_url: str
    created_at: datetime


class TestResultResponse(BaseModel):
    id: str
    test_run_id: str
    test_name: str
    class_name: str | None = None
    status: str
    duration_seconds: float | None = None
    failure_message: str | None = None
    failure_output: str | None = None
