import discord
from discord.ext import commands
import json

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.level_roles_file = "level_roles.json"
        self.user_data_file = "server_user_data.json"
        self.level_roles = self.load_json(self.level_roles_file)
        self.user_data = self.load_json(self.user_data_file)

    def load_json(self, filename):
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_json(self, filename, data):
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

    def calculate_exp(self, level):
        return 100 * (1.8 ** (level - 1))

    def get_level_from_exp(self, exp):
        level = 0
        while exp >= self.calculate_exp(level + 1):
            level += 1
        return level

    def get_role_for_level(self, level):
        eligible_roles = {int(k): v for k, v in self.level_roles["roles"].items() if int(k) <= level}
        return eligible_roles[max(eligible_roles)] if eligible_roles else None

    async def update_roles(self, member, new_level):
        role_id = self.get_role_for_level(new_level)
        if role_id:
            role = member.guild.get_role(int(role_id))
            if role and role not in member.roles:
                await member.add_roles(role)

 


    @commands.command(name="set_max_level")
    @commands.has_permissions(administrator=True)
    async def set_max_level(self, ctx, max_level: int):
        self.level_roles["roles"][str(max_level)] = ""  # Placeholder, admin should set role manually
        self.save_json(self.level_roles_file, self.level_roles)
        await ctx.send(f"✅ Maximum level has been updated to {max_level}.")

    @commands.command(name="add_level_role")
    @commands.has_permissions(administrator=True)
    async def add_level_role(self, ctx, level: int, role: discord.Role):
        self.level_roles["roles"][str(level)] = str(role.id)
        self.save_json(self.level_roles_file, self.level_roles)
        await ctx.send(f"✅ Role {role.name} has been assigned to Level {level}.")

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):
        sorted_users = sorted(self.user_data.items(), key=lambda x: x[1]["exp"], reverse=True)[:10]
        embed = discord.Embed(title="Leaderboard", color=discord.Color.blue())
        for i, (user_id, data) in enumerate(sorted_users, 1):
            user = await self.bot.fetch_user(int(user_id))
            embed.add_field(name=f"{i}. {user.name}", value=f"Level: {data['level']} | EXP: {data['exp']}", inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Leveling(bot))
