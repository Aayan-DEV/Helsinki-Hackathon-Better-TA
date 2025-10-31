from django.http import JsonResponse
from helpers.supabase.supabase_client import get_supabase

def ping_supabase(request):
    try:
        supabase = get_supabase()
        res = supabase.table("YOUR_TABLE").select("*").limit(1).execute()
        return JsonResponse({"ok": True, "count": len(res.data), "data": res.data})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)