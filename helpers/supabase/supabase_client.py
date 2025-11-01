from typing import Optional
from supabase import create_client, Client
from django.conf import settings

_supabase: Optional[Client] = None
_supabase_service: Optional[Client] = None

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_ANON_KEY in environment")
        _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    return _supabase

def get_supabase_service() -> Client:
    global _supabase_service
    if _supabase_service is None:
        if not settings.SUPABASE_URL or not getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', None):
            raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY; set it to your service role key")
        _supabase_service = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    return _supabase_service