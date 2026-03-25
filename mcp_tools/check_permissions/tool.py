import json

def check_permissions(user: str, action: str) -> str:
    """
    Checks if a user has the necessary permissions to perform a specific action.
    """
    try:
        # Example permission check logic
        permissions = {
            "admin": ["read", "write", "delete"],
            "user": ["read"]
        }
        if user in permissions and action in permissions[user]:
            return json.dumps({"result": "allowed"})
        else:
            return json.dumps({"result": "denied"})
    except Exception as e:
        return json.dumps({"error": str(e)})