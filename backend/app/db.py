"""Supabase client.

Uses the service-role key, so every query here bypasses Row Level Security.
This module must never be reachable from the browser.
"""

from functools import lru_cache

from supabase import Client, create_client

from app import config


@lru_cache(maxsize=1)
def get_client() -> Client:
    """Return the process-wide Supabase client."""
    return create_client(config.SUPABASE_URL, config.SUPABASE_SECRET_KEY)
