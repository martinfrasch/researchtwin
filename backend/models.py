"""Pydantic models for API requests and responses."""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr = Field(..., max_length=254)
    tier: int = Field(default=3, ge=1, le=3)
    semantic_scholar_id: str = Field(default="", max_length=20)
    google_scholar_id: str = Field(default="", max_length=20)
    github_username: str = Field(default="", max_length=39)
    figshare_search_name: str = Field(default="", max_length=100)
    orcid: str = Field(default="", max_length=25)
    llm_api_key: str = Field(default="", max_length=256)
    llm_provider: str = Field(default="")
    website: str = Field(default="")  # honeypot — hidden field, bots fill it

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not re.match(r"^[\w\s\-'.]+$", v, re.UNICODE):
            raise ValueError("Name contains invalid characters")
        return v.strip()

    @field_validator("semantic_scholar_id")
    @classmethod
    def validate_ss_id(cls, v):
        if v and not re.match(r"^[0-9]{1,20}$", v):
            raise ValueError("Semantic Scholar ID must be numeric")
        return v

    @field_validator("google_scholar_id")
    @classmethod
    def validate_gs_id(cls, v):
        if v and not re.match(r"^[a-zA-Z0-9_-]{1,20}$", v):
            raise ValueError("Google Scholar ID must be alphanumeric")
        return v

    @field_validator("github_username")
    @classmethod
    def validate_gh_user(cls, v):
        if v and not re.match(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$", v):
            raise ValueError("Invalid GitHub username format")
        return v

    @field_validator("orcid")
    @classmethod
    def validate_orcid(cls, v):
        if v and not re.match(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$", v):
            raise ValueError("ORCID must be in format XXXX-XXXX-XXXX-XXXX")
        return v

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v):
        if v and v not in {"perplexity", "openai"}:
            raise ValueError("Unsupported LLM provider. Choose from: perplexity, openai")
        return v


class RegisterResponse(BaseModel):
    slug: str
    display_name: str
    tier: int
    message: str


class RequestUpdateRequest(BaseModel):
    slug: str = Field(..., min_length=2, max_length=128)
    email: EmailStr = Field(..., max_length=254)


class ProfileUpdateRequest(BaseModel):
    slug: str = Field(..., min_length=2, max_length=128)
    code: str = Field(..., min_length=6, max_length=6)
    semantic_scholar_id: str = Field(default="", max_length=20)
    google_scholar_id: str = Field(default="", max_length=20)
    github_username: str = Field(default="", max_length=39)
    figshare_search_name: str = Field(default="", max_length=100)
    orcid: str = Field(default="", max_length=25)
    llm_api_key: str = Field(default="", max_length=256)
    llm_provider: str = Field(default="", max_length=20)

    @field_validator("code")
    @classmethod
    def validate_code(cls, v):
        if not re.match(r"^\d{6}$", v):
            raise ValueError("Code must be exactly 6 digits")
        return v

    @field_validator("semantic_scholar_id")
    @classmethod
    def validate_ss_id(cls, v):
        if v and not re.match(r"^[0-9]{1,20}$", v):
            raise ValueError("Semantic Scholar ID must be numeric")
        return v

    @field_validator("google_scholar_id")
    @classmethod
    def validate_gs_id(cls, v):
        if v and not re.match(r"^[a-zA-Z0-9_-]{1,20}$", v):
            raise ValueError("Google Scholar ID must be alphanumeric")
        return v

    @field_validator("github_username")
    @classmethod
    def validate_gh_user(cls, v):
        if v and not re.match(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$", v):
            raise ValueError("Invalid GitHub username format")
        return v

    @field_validator("orcid")
    @classmethod
    def validate_orcid(cls, v):
        if v and not re.match(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$", v):
            raise ValueError("ORCID must be in format XXXX-XXXX-XXXX-XXXX")
        return v

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v):
        if v and v not in {"perplexity", "openai"}:
            raise ValueError("Unsupported LLM provider. Choose from: perplexity, openai")
        return v


class ProfileUpdateResponse(BaseModel):
    slug: str
    message: str
