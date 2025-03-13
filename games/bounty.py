import random
import logging
from datetime import datetime, timedelta
import discord
from discord import app_commands
from typing import Optional
from data_manager import get_user_data, update_rubles, update_user_data

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class BountyCommandError(Exception):
    """Custom exception for bounty command-related errors."""
    pass

class BountyEvent:
    def __init__(self):
        self.active = False
        self.start_time = None
        self.total_prize = 0
        self.image_url = None
        self.participants = {}
        self.winner = None
        self.blank_box_users = set()  # Track users who hit blank box
        self.participant_role_id = 1340367044226449418  # Store participant role ID
        self.participant_count = 0  # Track number of users with role

global_bounty_event = BountyEvent()

async def bounty_command(ctx, reward: int, image_url: Optional[str] = None):
    """
    Start a bounty event with specified reward and optional image.
    
    Args:
        ctx (discord.Context or InteractionContext): The context of the command
        reward (int): Total reward rubles for the bounty
        image_url (str, optional): URL of the event image
    """
    try:
        # Check admin permissions
        if not ctx.author.guild_permissions.administrator:
            raise BountyCommandError("Only administrators can start a bounty event")

        # Reset and initialize bounty event
        global global_bounty_event
        global_bounty_event = BountyEvent()
        global_bounty_event.active = True
        global_bounty_event.start_time = datetime.now()
        global_bounty_event.total_prize = reward
        global_bounty_event.image_url = image_url

        # Count users with participant role
        participant_role = ctx.guild.get_role(global_bounty_event.participant_role_id)
        if participant_role:
            global_bounty_event.participant_count = len(participant_role.members)

        # Create embed for bounty announcement
        embed = discord.Embed(
            title="🏆 Bounty Event Launched! 🏆", 
            description=(
                f"**Prize Pool**: <a:Rubles:1344705820222292011> {reward} Rubles\n\n"
                "**Pull Rates**:\n"
                "- 1 Pull: 160 Rubles\n"
                "- 10 Pulls: 1600 Rubles\n\n"
                "**Chances**:\n"
                "- Winning Chance: Dynamic based on pulls\n"
                "- Pity System: More chances with consecutive pulls\n\n"
                f"**Eligible Players**: {global_bounty_event.participant_count}\n"
                f"*Only users with <@&{global_bounty_event.participant_role_id}> role can participate*"
            ), 
            color=discord.Color.gold()
        )
        
        if image_url:
            embed.set_image(url=image_url)
        
        embed.set_footer(text="Event Duration: 30 Minutes!")
        
        await ctx.send(embed=embed)
        logger.info(f"Bounty event started by {ctx.author} with {reward} rubles")

    except BountyCommandError as bounty_error:
        await ctx.send(f"<a:Animated_Cross:1334810307205398529> Bounty Error: {bounty_error}")
        logger.error(f"Bounty start error: {bounty_error}")
    except Exception as unexpected_error:
        await ctx.send("An unexpected error occurred starting the bounty event.")
        logger.error(f"Unexpected bounty start error: {unexpected_error}", exc_info=True)

async def pulls_command(ctx, amount: int = 1):
    """
    Execute bounty pulls with 50% win rate and guaranteed bounty after 70 pulls.
    """
    try:
        global global_bounty_event
        if not global_bounty_event.active:
            raise BountyCommandError("No active bounty event!")

        # Check if user has participant role
        participant_role = ctx.guild.get_role(global_bounty_event.participant_role_id)
        if not participant_role or participant_role not in ctx.author.roles:
            raise BountyCommandError(f"You need the <@&{global_bounty_event.participant_role_id}> role to participate!")

        # Check if event has timed out (30 minutes)
        event_duration = datetime.now() - global_bounty_event.start_time
        if event_duration > timedelta(minutes=30):
            global_bounty_event.active = False
            raise BountyCommandError("Bounty event has ended! No winner this time.")

        server_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        user_data = get_user_data(server_id, user_id)

        # Pull cost determination
        if amount == 1:
            cost = 160
            pulls = 1
        elif amount == 10:
            cost = 1600
            pulls = 10
        else:
            raise BountyCommandError("Invalid pull amount!")

        # Check rubles
        if user_data.get('currency', 0) < cost:
            raise BountyCommandError(f"Insufficient rubles! You need {cost} rubles.")

        # Initialize participant tracking
        if user_id not in global_bounty_event.participants:
            global_bounty_event.participants[user_id] = {
                'pulls': 0,
                'total_pulls': 0
            }

        participant_data = global_bounty_event.participants[user_id]
        participant_data['pulls'] += pulls
        participant_data['total_pulls'] += pulls

        # Guaranteed win after 70 pulls
        if participant_data['total_pulls'] >= 70:
            # Award bounty prize and end event
            prize_amount = global_bounty_event.total_prize
            global_bounty_event.winner = user_id
            global_bounty_event.active = False
            
            update_rubles(server_id, user_id, prize_amount)

            embed = discord.Embed(
                title="🏆 GUARANTEED BOUNTY WIN!", 
                description=(
                    f"Congratulations {ctx.author.mention}! 🎊\n"
                    f"After {participant_data['total_pulls']} pulls, you won the bounty!\n"
                    f"Prize: <a:Rubles:1344705820222292011> {prize_amount} Rubles"
                ),
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
            return

        # 40% win chance
        if random.random() < 0.4:
            # Winner found - award prize and end event
            prize_amount = global_bounty_event.total_prize
            global_bounty_event.winner = user_id
            global_bounty_event.active = False
            
            update_rubles(server_id, user_id, prize_amount)
            
            embed = discord.Embed(
                title="🎉 BOUNTY WINNER!", 
                description=(
                    f"Congratulations {ctx.author.mention}! 🎊\n"
                    f"You won the bounty!\n"
                    f"Prize: <a:Rubles:1344705820222292011> {prize_amount} Rubles\n"
                    f"Total Pulls: {participant_data['total_pulls']}"
                ),
                color=discord.Color.gold()
            )
        else:
            embed = discord.Embed(
                title="😢 Better Luck Next Time!", 
                description=(
                    f"{ctx.author.mention}, no prize this time.\n"
                    f"Total Pulls: {participant_data['total_pulls']}\n"
                    "Guaranteed win at 70 pulls!"
                ),
                color=discord.Color.red()
            )

        # Deduct pull cost
        update_rubles(server_id, user_id, -cost)
        await ctx.send(embed=embed)

    except BountyCommandError as bounty_error:
        await ctx.send(f"<a:Animated_Cross:1344705833627549748> Bounty Pull Error: {bounty_error}")
        logger.error(f"Bounty pull error: {bounty_error}")
    except Exception as unexpected_error:
        await ctx.send("An unexpected error occurred during your bounty pull.")
        logger.error(f"Unexpected bounty pull error: {unexpected_error}", exc_info=True)