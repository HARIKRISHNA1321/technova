
import json
import os
import time
from typing import Any, Dict
from supabase import create_client, Client

class LocalStateStore:
    def __init__(self, filepath="state_store.json"):
        self.filepath = filepath
        self.supabase_url = os.getenv("SUPABASE_URL", "").strip()
        self.supabase_key = os.getenv("SUPABASE_KEY", "").strip()
        self.client = None
        if self.supabase_url and self.supabase_key:
            try:
                self.client = create_client(self.supabase_url, self.supabase_key)
            except Exception as e:
                print(f"[SUPABASE ERROR] Failed to initialize Supabase client: {e}")

    def load_state(self) -> Dict[str, Any]:
        local_state = {}
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    local_state = json.load(f)
            except Exception:
                pass

        supabase_state = {}
        if self.client:
            try:
                res = self.client.table("app_state").select("state").eq("id", "main_state").execute()
                if res.data and len(res.data) > 0:
                    supabase_state = res.data[0]["state"]
            except Exception as e:
                print(f"[SUPABASE ERROR] Failed to load state: {e}")

        # Compare timestamps to return the latest state
        local_time = local_state.get("last_updated", 0)
        supabase_time = supabase_state.get("last_updated", 0)
        
        if supabase_time > local_time:
            # Sync local file with the newer Supabase state
            try:
                with open(self.filepath, "w") as f:
                    json.dump(supabase_state, f, indent=2)
            except Exception:
                pass
            return supabase_state
            
        return local_state if local_state else supabase_state

    def save_state(self, state_dict: Dict[str, Any]):
        # Add timestamp
        state_dict["last_updated"] = time.time()
        
        # Always write to local storage first
        try:
            with open(self.filepath, "w") as f:
                json.dump(state_dict, f, indent=2)
        except Exception as e:
            print(f"[LOCAL STORE ERROR] Failed to save state locally: {e}")

        if self.client:
            try:
                self.client.table("app_state").upsert({"id": "main_state", "state": state_dict}).execute()
            except Exception as e:
                print(f"[SUPABASE ERROR] Failed to save state to Supabase: {e}")

    def update_field(self, key: str, value: Any):
        state = self.load_state()
        state[key] = value
        self.save_state(state)
