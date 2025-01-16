# data_manager.py
import json
import math

data_file = "server_user_data.json"

def load_data():
    try:
        with open(data_file, "r") as f:
            data = json.load(f)
            # Update existing server data to include background if not present
            for server_id in data:
                for user_id in data[server_id]:
                    if "background_url" not in data[server_id][user_id]:
                        data[server_id][user_id]["background_url"] = None
            return data
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(data_file, "w") as f:
        json.dump(data, f, indent=4)

server_data = load_data()

def get_user_data(server_id, user_id):
    server_id = str(server_id)
    user_id = str(user_id)
    
    if server_id not in server_data:
        server_data[server_id] = {}
    
    if user_id not in server_data[server_id]:
        server_data[server_id][user_id] = {
            "level": 0,
            "exp": 0,
            "currency": 0,
            "background_url": None
        }
    
    return server_data[server_id][user_id]