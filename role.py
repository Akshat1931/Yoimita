import json
from typing import Dict, Optional
import discord
import os

class RoleManager:
    def __init__(self):
        self.role_file = "level_roles.json"
        self.roles_data = self.load_roles()

    def load_roles(self) -> Dict:
        try:
            with open(self.role_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            default_roles = {
                "roles": {
                    "5": "1328742229010939975",
                    "10": "1328742369079722046",
                    "15": "1328742460146581514",
                    "20": "1328743756605821031",
                    "25": "1328742557571874877",
                    "30": "1328742621346267217",
                    "40": "1328742680037036112",
                    "50": "1328742745807917117",
                    "70": "1328742799306133626",
                    "90": "1328742843203715192",
                    "100": "1328742892339986564"
                }
            }
            self.save_roles(default_roles)
            return default_roles

    def save_roles(self, data: Dict):
        with open(self.role_file, "w") as f:
            json.dump(data, f, indent=4)

    def get_role_for_level(self, level: int) -> Optional[str]:
        """Get role ID for a specific level"""
        # Convert all keys to int for comparison
        roles = {int(k): v for k, v in self.roles_data["roles"].items()}
        
        # Find the highest role level that the user qualifies for
        eligible_levels = [lvl for lvl in roles.keys() if lvl <= level]
        if not eligible_levels:
            return None
            
        highest_eligible = max(eligible_levels)
        return roles[highest_eligible]

    async def handle_role_update(self, member: discord.Member, new_level: int):
        """Update user's roles based on their new level"""
        try:
            # Get all possible role IDs for levels up to and including the user's level
            eligible_roles = {
                int(role_id) for level, role_id in self.roles_data["roles"].items()
                if int(level) <= new_level
            }
            
            # Get current role IDs
            current_roles = {role.id for role in member.roles}
            
            # Add new roles
            for role_id in eligible_roles:
                if role_id not in current_roles:
                    role = member.guild.get_role(int(role_id))
                    if role:
                        await member.add_roles(role)
                        
            # Remove lower level roles if configured to do so
            level_roles = set(int(role_id) for role_id in self.roles_data["roles"].values())
            roles_to_remove = level_roles - eligible_roles
            
            for role_id in roles_to_remove:
                if role_id in current_roles:
                    role = member.guild.get_role(role_id)
                    if role:
                        await member.remove_roles(role)
                        
        except discord.Forbidden:
            raise discord.Forbidden("Bot doesn't have permission to manage roles")
        except Exception as e:
            raise Exception(f"Error updating roles: {e}")