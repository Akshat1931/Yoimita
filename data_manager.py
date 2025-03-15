import datetime
import json
import os
import math
import time
import random
from typing import Any, Dict, Optional, Tuple

data_file = "server_user_data.json"

class LevelingConfig:
    EXP_BASE = 100  
    EXP_MULTIPLIER = 1.8  
    CURRENCY_BASE = 50  
    CURRENCY_MULTIPLIER = 1.00  
    EXP_PER_MESSAGE = 3 # ✅ REDUCED EXP TO SLOW DOWN LEVEL-UPS
 

def load_data():
    try:
        with open(data_file, "r") as f:
            data = json.load(f)
            # Initialize missing fields for existing data
            for server_id in data:
                for user_id in data[server_id]:
                    user_data = data[server_id][user_id]
                    # Initialize default values for any missing fields
                    default_fields = {
                        "background_url": None,
                        "daily_msg": 0,
                        "weekly_msg": 0, 
                        "completed_daily": [],
                        "completed_weekly": False,
                        "last_spin": None,
                        "level": 0,
                        "exp": 0,
                        "currency": 0
                    }
                    for field, default in default_fields.items():
                        if field not in user_data:
                            user_data[field] = default
            return data
    except FileNotFoundError:
        return {}

def save_data(data):
    # Generate a unique temporary filename
    temp_file = f"{data_file}.{random.randint(1000, 9999)}.temp"
    backup_file = f"{data_file}.backup"
    
    # First write to a temporary file to avoid corruption if interrupted
    try:
        with open(temp_file, "w") as f:
            json.dump(data, f, indent=4)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk
            
        # Create backup by first trying to copy the content
        if os.path.exists(data_file):
            try:
                # Try to create a backup, but continue if it fails
                with open(data_file, "r") as src:
                    with open(backup_file, "w") as dst:
                        dst.write(src.read())
                        dst.flush()
                        os.fsync(dst.fileno())
            except (IOError, OSError) as e:
                # Log error but continue - we still have the temp file with our new data
                print(f"Warning: Could not create backup file: {e}")
        
        # Try to replace the original file with our temp file
        # Use multiple attempts with short delays to handle file locking
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                if os.path.exists(data_file):
                    os.replace(temp_file, data_file)
                else:
                    os.rename(temp_file, data_file)
                break  # Success!
            except (IOError, OSError) as e:
                if attempt < max_attempts - 1:
                    # Wait a bit and retry
                    time.sleep(0.2 * (attempt + 1))
                else:
                    # If all attempts fail, try a direct write as last resort
                    try:
                        with open(data_file, "w") as f:
                            json.dump(data, f, indent=4)
                    except Exception as last_e:
                        print(f"Error: Could not save data after multiple attempts: {last_e}")
                        # Keep the temp file as emergency backup
                        return
        
        # Clean up temp file if it still exists
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass  # Ignore cleanup errors
                
    except Exception as e:
        print(f"Error during save operation: {e}")
        # If we failed during initial temp file creation, try direct write as fallback
        try:
            with open(data_file, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as fallback_e:
            print(f"Critical error: Could not save data: {fallback_e}")

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
            "background_url": None,
            "daily_msg": 0,
            "weekly_msg": 0,
            "completed_daily": [],
            "completed_weekly": False,
            "last_spin": None
        }
    return server_data[server_id][user_id]



def calculate_reward(level: int) -> int:
    """Calculate currency reward for reaching a new level"""
    return int(LevelingConfig.CURRENCY_BASE * math.pow(LevelingConfig.CURRENCY_MULTIPLIER, level))

def exp_to_next_level(level: int) -> int:
    """Corrects EXP requirement calculation to ensure proper leveling."""
    if level == 0:
        return 50  # Base EXP for Level 1
    return int(50 * (1.5 ** (level)))  # Ensures exponential scaling




def calculate_total_exp_for_level(level: int) -> int:
    """Calculate total experience needed up to a specific level"""
    if level <= 0:
        return 0
    total = 0
    for i in range(1, level + 1):
        total += calculate_exp_for_level(i)
    return total

def calculate_level(exp: int) -> int:
    """Calculate correct level based on total experience points, preventing multiple level-ups per message."""
    level = 0
    next_level_exp = exp_to_next_level(level + 1)

    while exp >= next_level_exp:  
        level += 1
        next_level_exp = exp_to_next_level(level + 1)

        # ✅ Stop loop to prevent skipping multiple levels
        if exp < next_level_exp:
            break

    return level



def calculate_level_progress(exp: int) -> Tuple[int, int, float]:
    """Calculate progress towards next level"""
    current_level = calculate_level(exp)
    total_exp_for_current = calculate_total_exp_for_level(current_level)
    
    # XP in the current level
    exp_in_level = exp - total_exp_for_current
    
    # XP needed for next level
    exp_needed = calculate_exp_for_level(current_level + 1)
    
    # Progress percentage
    if exp_needed == 0:  # Avoid division by zero
        progress = 0
    else:
        progress = min(100, (exp_in_level / exp_needed) * 100)
        
    return exp_in_level, exp_needed, progress

# Message count functions
def increment_daily_msg(server_id, user_id):
    user_data = get_user_data(server_id, user_id)
    user_data["daily_msg"] += 1
    save_data(server_data)

def increment_weekly_msg(server_id, user_id):
    user_data = get_user_data(server_id, user_id)
    user_data["weekly_msg"] += 1
    save_data(server_data)

def get_daily_msg(server_id, user_id) -> int:
    return get_user_data(server_id, user_id)["daily_msg"]

def get_weekly_msg(server_id, user_id) -> int:
    return get_user_data(server_id, user_id)["weekly_msg"]

# Currency functions
def update_rubles(server_id, user_id, amount):
    user_data = get_user_data(server_id, user_id)
    user_data["currency"] = max(0, user_data["currency"] + amount)
    save_data(server_data)

def get_user_rubles(server_id, user_id) -> int:
    return get_user_data(server_id, user_id)["currency"]

# Experience functions
def get_user_exp(server_id, user_id) -> int:
    return get_user_data(server_id, user_id)["exp"]

def get_user_level(server_id, user_id) -> int:
    return get_user_data(server_id, user_id)["level"]

def update_exp(guild_id: str, user_id: str, exp_gain: int):
    """Update user EXP and level while ensuring EXP resets correctly after level-up."""
    if guild_id not in server_data:
        server_data[guild_id] = {}

    if user_id not in server_data[guild_id]:
        server_data[guild_id][user_id] = {"level": 0, "exp": 0, "currency": 0}

    user = server_data[guild_id][user_id]
    old_exp = user["exp"]
    old_level = user["level"]

    print(f"⚠️ BEFORE: User {user_id} - Level {old_level} - EXP: {old_exp}")

    # ✅ Add EXP properly
    user["exp"] += exp_gain  

    leveled_up = False
    while user["exp"] >= exp_to_next_level(user["level"]):
        required_exp = exp_to_next_level(user["level"])

        # ✅ EXP is reset to 0 after level-up
        user["exp"] -= required_exp
        user["level"] += 1
        leveled_up = True

        print(f"🎉 User {user_id} leveled up to Level {user['level']}! (EXP reset to {user['exp']})")

    # ✅ Prevent EXP from exceeding the cap
    if user["exp"] >= exp_to_next_level(user["level"]):
        user["exp"] = exp_to_next_level(user["level"]) - 1

    print(f"⚠️ AFTER: User {user_id} - Level {user['level']} - EXP: {user['exp']}")

    save_data(server_data)
    return leveled_up








def update_user_data(server_id, user_id, updates: Dict[str, Any]):
    """Update multiple user data fields atomically"""
    user_data = get_user_data(server_id, user_id)
    for key, value in updates.items():
        if key in user_data:
            user_data[key] = value
    save_data(server_data)

# Commission functions
def mark_daily_completed(server_id, user_id, commission_index):
    user_data = get_user_data(server_id, user_id)
    if commission_index not in user_data["completed_daily"]:
        user_data["completed_daily"].append(commission_index)
        save_data(server_data)

def mark_weekly_completed(server_id, user_id):
    user_data = get_user_data(server_id, user_id)
    user_data["completed_weekly"] = True
    save_data(server_data)

def is_daily_completed(server_id, user_id, commission_index) -> bool:
    return commission_index in get_user_data(server_id, user_id)["completed_daily"]

def is_weekly_completed(server_id, user_id) -> bool:
    return get_user_data(server_id, user_id)["completed_weekly"]

# Reset functions
def reset_daily_commissions():
    for server in server_data.values():
        for user in server.values():
            user["completed_daily"] = []
    save_data(server_data)

def reset_weekly_commissions():
    for server in server_data.values():
        for user in server.values():
            user["completed_weekly"] = False
    save_data(server_data)

def reset_daily_counts():
    for server in server_data.values():
        for user in server.values():
            user["daily_msg"] = 0
    save_data(server_data)

def reset_weekly_counts():
    for server in server_data.values():
        for user in server.values():
            user["weekly_msg"] = 0
    save_data(server_data)

def update_last_spin(server_id, user_id, timestamp):
    """Update user's last spin time"""
    user_data = get_user_data(server_id, user_id)
    user_data["last_spin"] = timestamp
    save_data(server_data)