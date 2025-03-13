from discord.ext import commands


ADMIN_ROLE_IDS = [997500121761730590, 921508022428270593, 1667999300153549341, 834316543877578753]  # Add your role IDs here

def is_owner_or_admin():
    async def predicate(ctx):
        return (ctx.author.id == ctx.bot.owner_id or 
                any(ctx.guild.get_role(role_id) in ctx.author.roles 
                    for role_id in ADMIN_ROLE_IDS))
    return commands.check(predicate)



