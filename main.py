import asyncio
from asyncio.log import logger
import datetime
import importlib
import logging
import os
import random
from socket import SocketType
from types import SimpleNamespace
from typing import Dict, List, Optional, Any
import discord
from discord.ext import commands, tasks
from discord import app_commands, Interaction
import json
import math
import aiohttp
from PIL import Image, ImageDraw, ImageFont
import io
from asyncio import sleep, timeout_at
import random
from datetime import datetime, timezone, timedelta
import time

from gamble.gambling import play_slots, play_crash

from data_manager import LevelingConfig, calculate_level, calculate_level_progress, calculate_reward, exp_to_next_level, get_user_exp, get_user_rubles, increment_daily_msg, increment_weekly_msg, server_data, get_user_data, save_data, update_exp, update_rubles
import data_manager
from games.bounty import pulls_command, bounty_command, BountyCommandError
from games.guess_the_number import play_guess_the_number
from games.trivia import play_trivia
from games.coin import play_coinflip
from games.br import start_battle_royale
from games.ttt import start_tictactoe
from gamble.newganba import play_blackjack, play_plinko
from gamble.gambling import play_coinflip, play_colorwheel
from games.rps import play_rps
from games.numberdual import play_mathquiz
from games.SPINTHEwheel import spin_command
from more_commands import GENSHIN_CARDS, CardDropView, GameManager, RoleApprovalView, global_reset_command, reset_command, RouletteView, store_manager
from more_commands import profile_transfer_command, MAX_BET, MAX_MINES, MIN_MINES, play_mines
from role import RoleManager
from tictactoe import tictactoe_bet, active_games, MIN_BET, TicTacToeView


LOADED_GAMES = {}

def load_games():
    global LOADED_GAMES
    games_dir = "games"
    for filename in os.listdir(games_dir):
        if filename.endswith(".py"):
            module_name = filename[:-3]
            module = importlib.import_module(f"{games_dir}.{module_name}")
            LOADED_GAMES[module_name] = module

load_games()

with open("config.json", "r") as config_file:
    config = json.load(config_file)

BOT_TOKEN = config["bot_token"]
BOT_OWNER_ID = int(config["owner_id"])

RANDOM_EVENTS = [
    play_guess_the_number, 
    play_trivia,
    start_battle_royale,
    start_tictactoe,
    play_rps,
    play_mathquiz,
]

# Store setup
STORE_FILE = "store.json"

def load_store():
    if os.path.exists(STORE_FILE):
        with open(STORE_FILE, "r") as file:
            return json.load(file)
    return {}

def save_store():
    with open(STORE_FILE, "w") as file:
        json.dump(store, file)

# Persistent store system
store = load_store()

RANDOM_CHANNELS = {
    "1318804968085651559": "1318804968085651559",
    "1327334550883405997": "1327334550883405997"
}

intents = discord.Intents.all()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)
data_file = "server_user_data.json"




def exp_to_next_level(level):
    return 100 * math.pow(1.8, level - 1)

def calculate_currency(level):
    return int(50 * (1.00 ** (level - 1)))



async def load_cogs():
    await bot.load_extension("leveling")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await load_cogs()
    print("Leveling system loaded.")
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    server_id = str(message.guild.id)
    user_id = str(message.author.id)
    
    user_data = get_user_data(server_id, user_id)
    current_exp = user_data["exp"]
    
    old_level = calculate_level(current_exp)
    
    new_exp = current_exp + LevelingConfig.EXP_PER_MESSAGE
    
    update_exp(server_id, user_id, new_exp)
    new_level = calculate_level(new_exp)
    
    if new_level > old_level:
        reward = calculate_reward(new_level)
        update_rubles(server_id, user_id, reward)
        await message.channel.send(f"🎉 {message.author.mention} leveled up to Level {new_level} and earned {reward} rubles!")

    await bot.process_commands(message)



@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_data = get_user_data(message.guild.id, message.author.id)
    
    # Update daily messages
    user_data["daily_messages"] = user_data.get("daily_messages", 0) + 1
    
    # Update weekly messages
    user_data["weekly_messages"] = user_data.get("weekly_messages", 0) + 1
    
    save_data(server_data)
    await bot.process_commands(message)


@tasks.loop(minutes=10)
async def random_event():
    print("Random event loop triggered")  # Debug print
    for channel_id in RANDOM_CHANNELS.values():
        try:
            channel = bot.get_channel(int(channel_id))
            if channel:
                print(f"Checking activity in channel {channel.name}")  # Debug print
                
                # Fetch the last 10 messages from the channel
                messages = [msg async for msg in channel.history(limit=10)]
                
                # Check if there are at least 5 messages in the last 10 minutes
                active_messages = [msg for msg in messages if (datetime.now(timezone.utc) - msg.created_at).total_seconds() < 600]
                
                if len(active_messages) >= 5:
                    print(f"Channel {channel.name} is active, sending event")  # Debug print
                    
                    # Send warning message
                    warning_msg = await channel.send("⚠️ A random event is approaching in 5 seconds! ⚠️")
                    await asyncio.sleep(5)  # Wait 5 seconds
                    
                    # Get and handle the random event
                    event = random.choice(RANDOM_EVENTS)
                    if callable(event):  # Check if the event is a function
                        await event(channel)  # Call the function with channel parameter
                    else:
                        # If it's a string message, send it directly
                        await channel.send(f"🎉 **Random Event!** 🎉\n{event}")
                    
                    # Delete the warning message (optional)
                    await warning_msg.delete()
                else:
                    print(f"Channel {channel.name} is not active enough, skipping event")  # Debug print
                
        except Exception as e:
            print(f"Error in random event for channel {channel_id}: {e}")

# Update the set_event_channel command to ensure proper storage
@bot.tree.command(name="set_event_channel", description="Set the current channel for random events")
async def set_event_channel(interaction: discord.Interaction):
    try:
        RANDOM_CHANNELS[str(interaction.guild_id)] = str(interaction.channel_id)
        print(f"Set event channel for guild {interaction.guild_id}: {interaction.channel_id}")  # Debug print
        await interaction.response.send_message("<a:animated_tick:1344705804007112724> This channel has been set for random events!", ephemeral=True)
        
        # Test message to verify channel is working
        channel = bot.get_channel(interaction.channel_id)
        if channel:
            await channel.send("🎯 Random events will now appear in this channel!")
    except Exception as e:
        await interaction.response.send_message(f"Error setting event channel: {e}", ephemeral=True)

@bot.tree.command(name="remove_event_channel", description="Remove the random events channel")
@app_commands.checks.has_permissions(administrator=True)
async def remove_event_channel(interaction: discord.Interaction):
    if str(interaction.guild_id) in RANDOM_CHANNELS:
        del RANDOM_CHANNELS[str(interaction.guild_id)]
        await interaction.response.send_message("Random events channel has been removed!", ephemeral=True)
    else:
        await interaction.response.send_message("No event channel was set!", ephemeral=True)

@bot.tree.command(name="test_event", description="Trigger a test event")
@app_commands.checks.has_permissions(administrator=True)
async def test_event(interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
    try:
        # If no channel is provided, use the default event channel
        if channel is None:
            channel_id = RANDOM_CHANNELS.get(str(interaction.guild_id))
            if not channel_id:
                await interaction.response.send_message("No event channel set. Use /set_event_channel first!", ephemeral=True)
                return
                
            channel = bot.get_channel(int(channel_id))
            if not channel:
                await interaction.response.send_message("Could not find the event channel. Please set it again.", ephemeral=True)
                return

        await interaction.response.send_message(f"Starting event in {channel.mention}...", ephemeral=True)
        
        # Send warning
        await channel.send("⚠️ Event starting in 5 seconds! ⚠️")
        await sleep(5)
        
        # Start event
        event = random.choice(RANDOM_EVENTS)
        if callable(event):
            await event(channel)
        else:
            await channel.send(f"🎉 **Event!** 🎉\n{event}")
        
    except Exception as e:
        print(f"Error in test_event: {e}")
        await interaction.followup.send("An error occurred. Please try again.", ephemeral=True)
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
        random_event.start()  # Start the random event loop
        print("Random event loop started.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# Constants for choices
COIN_CHOICES = ["heads", "tails"]
DICE_NUMBERS = list(range(2, 13))  # 2-12
COLOR_CHOICES = ["red", "black", "green"]

# Command for Coinflip
@bot.tree.command(name="coinflip", description="Bet on heads or tails!")
@app_commands.describe(bet="The amount to bet [1-2000]", choice="Your choice: heads or tails")
async def coinflip(
    interaction: discord.Interaction,
    bet: app_commands.Range[int, 10, 2000],  # Minimum bet of 10, Maximum bet of 2000
    choice: str,
):
    if choice.lower() not in COIN_CHOICES:
        await interaction.response.send_message(
            "<a:Animated_Cross:1344705833627549748> Invalid choice! Please choose 'heads' or 'tails'.",
            ephemeral=True
        )
        return

    try:
        await play_coinflip(interaction, bet, choice)
    except Exception as e:
        await interaction.response.send_message(
            "<a:Animated_Cross:1344705833627549748> An unexpected error occurred. Please try again.",
            ephemeral=True
        )
        logger.error(f"Error in coinflip command: {e}", exc_info=True)

@coinflip.autocomplete("choice")
async def coinflip_choice_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=choice, value=choice)
        for choice in COIN_CHOICES
        if current.lower() in choice.lower()
    ]

# Command for Color Wheel
@bot.tree.command(name="colorwheel", description="Bet on the color wheel!")
@app_commands.describe(bet="The amount to bet", color="Pick a color: red, black, or green")
async def colorwheel(
    interaction: Interaction,
    bet: app_commands.Range[int, 10, None],  # Minimum bet of 10
    color: str,
):
    # Check if user already has an active game
    if interaction.user.id in active_games:
        await interaction.response.send_message(
            "<a:Animated_Cross:1344705833627549748> You already have an active game! Please finish it before starting a new one.",
            ephemeral=True
        )
        return

    try:
        # Add the game to active games before starting
        active_games[interaction.user.id] = "colorwheel"
        
        # Call the original play function
        await play_colorwheel(interaction, bet, color)
        
        # Remove the game from active games after it's complete
        if interaction.user.id in active_games:
            del active_games[interaction.user.id]
            
    except Exception as e:
        # Make sure to clean up even if there's an error
        if interaction.user.id in active_games:
            del active_games[interaction.user.id]
        
        await interaction.response.send_message(
            "<a:Animated_Cross:1344705833627549748> An unexpected error occurred. Please try again.",
            ephemeral=True
        )
        print(f"Colorwheel game error: {str(e)}")  # For logging

@colorwheel.autocomplete("color")
async def colorwheel_color_autocomplete(
    interaction: Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=color, value=color)
        for color in COLOR_CHOICES
        if current.lower() in color.lower()
    ]

@bot.tree.command(name="balance", description="Check your currency balance.")
async def balance(interaction: discord.Interaction, member: discord.Member = None):
    # If no member is specified, default to the command user
    target_member = member or interaction.user
    
    user = get_user_data(interaction.guild_id, target_member.id)
    currency = user["currency"]
    
    embed = discord.Embed(
        title=f"{target_member.name}'s Balance",
        description=f"**Currency:** {currency} <a:Rubles:1344705820222292011>",
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="profile", description="View your profile.")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    try:
        # If no member is specified, default to the command user
        target_member = member or interaction.user
        
        user = get_user_data(str(interaction.guild_id), str(target_member.id))
        level = user.get("level", 0)
        exp = user.get("exp", 0)
        next_level_exp = exp_to_next_level(level)
        next_level_exp = max(next_level_exp, 1)  # Prevent division by zero
        progress = round((exp / next_level_exp) * 100)  # ✅ Rounds progress %


        
        embed = discord.Embed(
            title=f"{target_member.display_name}'s Profile",
            color=discord.Color.gold()
        )
        
        if target_member.display_avatar:
            embed.set_thumbnail(url=target_member.display_avatar.url)
            
        embed.add_field(name="Level", value=f":arrow_arrow: {level}", inline=False)
        embed.add_field(name="Currency", value=f":arrow_arrow: {user.get('currency', 0)} :Rubles:", inline=False)
        embed.add_field(
            name="Progress to Next Level",
            value=f":arrow_arrow: {progress}% ({round(exp):,}/{round(next_level_exp):,} EXP)",

            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        error_embed = discord.Embed(
            title=":Animated_Cross: Error",
            description="An error occurred while fetching profile data. Please try again.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)


@bot.tree.command(name="fine", description="Fine a user an amount of currency.")
@app_commands.describe(user="The user to fine.", amount="The amount to fine.")
async def fine(interaction: discord.Interaction, user: discord.User, amount: int):
    try:
        # Check for admin permissions instead of bot owner
        if not interaction.user.guild_permissions.administrator:
            error_embed = discord.Embed(
                title=f"{discord.utils.get(interaction.guild.emojis, name='error')} Access Denied",
                description="This command is restricted to server administrators only.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        if amount <= 0:
            error_embed = discord.Embed(
                title=f"{discord.utils.get(interaction.guild.emojis, name='error')} Invalid Amount",
                description="The amount must be greater than 0.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        # Process the fine
        user_data = get_user_data(interaction.guild_id, user.id)
        user_data["currency"] -= amount
        save_data(server_data)

        # Create channel notification embed
        fine_embed = discord.Embed(
            title=f"<a:Warning:1334552043863543878> rubles Fine",
            description="A fine has been imposed!",
            color=discord.Color.red()
        ).set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        fine_embed.add_field(
            name="👮 Fined By",
            value=interaction.user.mention,
            inline=True
        )
        
        fine_embed.add_field(
            name="👤 Recipient",
            value=user.mention,
            inline=True
        )
        
        fine_embed.add_field(
            name="💸 Fine Amount",
            value=f"**{amount:,}** <a:Rubles:1344705820222292011>",
            inline=True
        )
        
        fine_id = hex(int(time.time()))[2:].upper()
        fine_embed.set_footer(text=f"Fine ID: {fine_id}")

        # Send channel message
        await interaction.response.send_message(embed=fine_embed)
        
        # Create and send DM notification
        try:
            dm_embed = discord.Embed(
                title=f"⚠️ Rubles Fine Received",
                description=f"You have been fined in {interaction.guild.name}!",
                color=discord.Color.red()
            )
            
            dm_embed.add_field(
                name="💸 Fine Amount",
                value=f"**{amount:,}** <a:Rubles:1344705820222292011>",
                inline=True
            )
            
            dm_embed.add_field(
                name="👮 Fined By",
                value=interaction.user.name,
                inline=True
            )
            
            dm_embed.add_field(
                name="📊 Your New Balance",
                value=f"**{user_data['currency']:,}** <a:Rubles:1344705820222292011>",
                inline=True
            )
            
            dm_embed.set_footer(text=f"Fine ID: {fine_id}")
            
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            await interaction.followup.send(
                embed=discord.Embed(
                    title=f"<a:Error:1334553891928539218> Notice",
                    description=f"Unable to send fine notification to {user.mention}. They may have DMs disabled.",
                    color=discord.Color.orange()
                )
            )
        except Exception as e:
            await interaction.followup.send(
                embed=discord.Embed(
                    title=f"<a:Error:1334553891928539218> Notice",
                    description=f"Failed to send DM notification: {str(e)}",
                    color=discord.Color.orange()
                )
            )

    except Exception as e:
        error_embed = discord.Embed(
            title=f"<a:Error:1334553891928539218> Error",
            description=f"An error occurred while processing the fine: {str(e)}",
            color=discord.Color.red()
        )
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="pay", description="Pay another user from your balance")
@app_commands.describe(
    user="The user to pay", 
    amount="The amount to pay",
    message="Optional message to send with payment"
)
async def pay(interaction: discord.Interaction, user: discord.User, amount: int, message: str = None):
    try:
        # Basic validation checks
        if user.id == interaction.user.id:
            error_embed = discord.Embed(
                title="Invalid Transaction",
                description="You cannot pay yourself!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        if amount <= 0:
            error_embed = discord.Embed(
                title="Invalid Amount",
                description="The amount must be greater than 0.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        # Get user data
        sender_data = get_user_data(interaction.guild_id, interaction.user.id)
        receiver_data = get_user_data(interaction.guild_id, user.id)

        # Check if sender has enough balance
        if sender_data["currency"] < amount:
            error_embed = discord.Embed(
                title="Insufficient Balance",
                description=f"You don't have enough rubles! Your balance: **{sender_data['currency']:,}**",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        # Process the transaction
        sender_data["currency"] -= amount
        receiver_data["currency"] += amount
        save_data(server_data)

        # Generate transaction ID
        transaction_id = hex(int(time.time()))[2:].upper()

        # Create channel notification embed with simplified design
        pay_embed = discord.Embed(
            title=f"<a:tick:1344705817290473554> Transaction Complete",
            description=f"A payment has been processed successfully!",
            color=discord.Color.green()
        )
        
        if interaction.guild.icon:
            pay_embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url)
        else:
            pay_embed.set_author(name=interaction.guild.name)
        
        pay_embed.add_field(
            name="Payment Details",
            value=(
                f"**Sender:** {interaction.user.mention}\n"
                f"**Recipient:** {user.mention}\n"
                f"**Amount:** {amount:,} <a:Rubles:1344705820222292011>"
            ),
            inline=False
        )

        if message:
            pay_embed.add_field(
                name="Message",
                value=message,
                inline=False
            )
        
        pay_embed.set_footer(text=f"Transaction ID: {transaction_id} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Send channel message
        await interaction.response.send_message(embed=pay_embed)
        
        # Send DM to recipient with simplified design
        try:
            receiver_dm = discord.Embed(
                title=f"<a:animated_tick:1344705804007112724> Payment Received",
                description=(
                    f"**Amount:** {amount:,} <a:Rubles:1344705820222292011>\n"
                    f"**From:** {interaction.user.name}\n"
                    f"**Your New Balance:** {receiver_data['currency']:,} <a:Rubles:1344705820222292011>\n"
                    f"**Server:** {interaction.guild.name}"
                ),
                color=discord.Color.green()
            )
            if message:
                receiver_dm.add_field(
                    name="Message",
                    value=message,
                    inline=False
                )
            receiver_dm.set_footer(text=f"Transaction ID: {transaction_id}")
            await user.send(embed=receiver_dm)
        except discord.Forbidden:
            pass
        
        # Send DM to sender with simplified design
        try:
            sender_dm = discord.Embed(
                title=f"<a:animated_tick:1344705804007112724> Payment Sent",
                description=(
                    f"**Amount:** {amount:,} <a:Rubles:1344705820222292011>\n"
                    f"**To:** {user.name}\n"
                    f"**Your New Balance:** {sender_data['currency']:,} <a:Rubles:1344705820222292011>\n"
                    f"**Server:** {interaction.guild.name}"
                ),
                color=discord.Color.green()
            )
            if message:
                sender_dm.add_field(
                    name="Message",
                    value=message,
                    inline=False
                )
            sender_dm.set_footer(text=f"Transaction ID: {transaction_id}")
            await interaction.user.send(embed=sender_dm)
        except discord.Forbidden:
            pass

    except Exception as e:
        error_embed = discord.Embed(
            title="Error",
            description=f"An error occurred while processing the payment: {str(e)}",
            color=discord.Color.red()
        )
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="give", description="Give another user an amount of currency without deducting from your balance.")
@app_commands.describe(user="The user to give currency to.", amount="The amount to give.")
async def give(interaction: discord.Interaction, user: discord.User, amount: int):
    try:
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        if not interaction.user.guild_permissions.administrator:
            error_embed = discord.Embed(
                title="Access Denied", 
                description="This command is restricted to server administrators only.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        if amount <= 0:
            error_embed = discord.Embed(
                title="Invalid Amount",
                description="The amount must be greater than 0.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        if str(interaction.guild.id) not in server_data:
            server_data[str(interaction.guild.id)] = {}
        if str(user.id) not in server_data[str(interaction.guild.id)]:
            server_data[str(interaction.guild.id)][str(user.id)] = {"currency": 0}

        recipient_data = server_data[str(interaction.guild.id)][str(user.id)]
        recipient_data["currency"] += amount
        
        try:
            save_data(server_data)
        except Exception as e:
            error_embed = discord.Embed(
                title="Save Error",
                description="Failed to save data. Please try again.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        grant_id = hex(int(time.time()))[2:].upper()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Create channel notification embed with blue theme
        give_embed = discord.Embed(
            title=f"<a:tick:1344705817290473554> rubles Grant Successfully Sent",
            description=(
                f"<a:arrow_arrow:1344705810516676608> A rubles grant has been awarded by {interaction.user.mention} to {user.mention}"
            ),
            color=0x3498db  # Blue color
        )

        try:
            give_embed.set_author(
                name=interaction.guild.name,
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )
        except:
            pass

        give_embed.add_field(
            name="Transaction Details",
            value=(
                f"<:money_bag:1344705814774157372> **Amount:** {amount:,} <a:Rubles:1344705820222292011>\n"
                f"<a:arrow_arrow:1344705810516676608> **From:** {interaction.user.mention}\n"
                f"<a:arrow_arrow:1344705810516676608> **To:** {user.mention}"
            ),
            inline=False
        )
        
        give_embed.set_footer(text=f"Grant ID: {grant_id} • {timestamp}")

        # Send channel message
        await interaction.response.send_message(embed=give_embed)
        
        # Send DM to recipient
        try:
            dm_embed = discord.Embed(
                title=f"<a:animated_tick:1344705804007112724>Rubles Grant Received",
                description=f"You have received a special rubles grant in {interaction.guild.name}!",
                color=0x3498db
            )
            
            dm_embed.add_field(
                name="Grant Details",
                value=(
                    f"💰 **Amount:** {amount:,} <a:Rubles:1344705820222292011>\n"
                    f"➡️ **From:** {interaction.user.name}\n"
                    f"➡️ **New Balance:** {recipient_data['currency']:,} <a:Rubles:1344705820222292011>"
                ),
                inline=False
            )
            
            dm_embed.set_footer(text=f"Grant ID: {grant_id}")
            
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass
        except Exception as e:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Notice",
                    description=f"Failed to send DM notification: {str(e)}",
                    color=discord.Color.orange()
                ),
                ephemeral=True
            )

    except Exception as e:
        error_embed = discord.Embed(
            title="Error",
            description=f"An error occurred: {str(e)}",
            color=discord.Color.red()
        )
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=error_embed, ephemeral=True)


@bot.tree.command(name="upload_background", description="Upload a custom background for your level card")
async def upload_background(interaction: discord.Interaction, image: discord.Attachment):
    try:
        # Check if the uploaded file is an image
        if not image.content_type.startswith('image/'):
            await interaction.response.send_message("Please upload an image file.", ephemeral=True)
            return

        # Check file size (limit to 5MB)
        if image.size > 5 * 1024 * 1024:
            await interaction.response.send_message("Image file size must be under 5MB.", ephemeral=True)
            return

        # Get user data using the same method as level command
        user = get_user_data(interaction.guild_id, interaction.user.id)

        
        # Store the image URL
        user["background_url"] = image.url
        
        # Save the updated user data
        save_data(server_data)
       

        await interaction.response.send_message("Background image updated successfully! Use /level to see your new card.", ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="remove_background", description="Remove your custom background")
async def remove_background(interaction: discord.Interaction):
    try:
        # Get user data using the same method as level command
        user = get_user_data(interaction.guild_id, interaction.user.id)
        
        # Check if user has a background set
        if not user.get("background_url"):
            await interaction.response.send_message("You don't have a custom background set.", ephemeral=True)
            return
        
        # Remove background
        user["background_url"] = None
        
        # Save the updated user data
        save_data(server_data)
        
        await interaction.response.send_message("Background removed successfully! Your level card will now use the default background.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

# ... (previous code remains the same until the level command)

@bot.tree.command(name="level", description="Check your level and progress.")
async def level(interaction: discord.Interaction):
    try:
        await interaction.response.send_message("Generating level card...")
    except:
        return

    user = get_user_data(interaction.guild_id, interaction.user.id)
    level = user["level"]
    exp = int(user["exp"])
    next_level_exp = int(exp_to_next_level(level))
    progress = min(max(exp / next_level_exp if next_level_exp > 0 else 0, 0), 1)

    width, height = 600, 300
    background_color = (22, 27, 34)
    accent_color = (88, 166, 255)
    bar_color = accent_color
    bar_background = (47, 54, 61)
    text_color = (255, 255, 255)
    secondary_text_color = (139, 148, 158)

    image = Image.new("RGBA", (width, height), color=(0, 0, 0, 0))
    
    if user.get("background_url"):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(user["background_url"]) as response:
                    background_data = await response.read()
                    background_image = Image.open(io.BytesIO(background_data))
                    background_image = background_image.convert('RGBA')
                    background_image = background_image.resize((width, height), Image.Resampling.LANCZOS)
                    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 128))
                    background_image = Image.alpha_composite(background_image, overlay)
                    
                    image = background_image
        except Exception as e:
            print(f"Error loading background: {e}")
            draw = ImageDraw.Draw(image)
            for y in range(height):
                r = int(32 + (22 - 32) * y / height)
                g = int(37 + (27 - 37) * y / height)
                b = int(44 + (34 - 44) * y / height)
                draw.line([(0, y), (width, y)], fill=(r, g, b))
    else:
        draw = ImageDraw.Draw(image)
        for y in range(height):
            r = int(32 + (22 - 32) * y / height)
            g = int(37 + (27 - 37) * y / height)
            b = int(44 + (34 - 44) * y / height)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

    draw = ImageDraw.Draw(image)

    avatar_glow_size = 120
    avatar_glow = Image.new('RGBA', (avatar_glow_size, avatar_glow_size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(avatar_glow)
    for i in range(10):
        alpha = int(100 - i * 10)
        glow_draw.ellipse([i, i, avatar_glow_size-i, avatar_glow_size-i], 
                         fill=(accent_color[0], accent_color[1], accent_color[2], alpha))
    image.paste(avatar_glow, (30, 20), avatar_glow)

    try:
        avatar_size = 100
        avatar_url = str(interaction.user.display_avatar.replace(size=256).url)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as response:
                avatar_data = await response.read()
                avatar_image = Image.open(io.BytesIO(avatar_data))
        
        avatar_image = avatar_image.convert('RGBA')
        avatar_image = avatar_image.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, avatar_size - 1, avatar_size - 1), fill=255)
        output = Image.new('RGBA', (avatar_size, avatar_size), (0, 0, 0, 0))
        output.paste(avatar_image, (0, 0))
        output.putalpha(mask)
        
        image.alpha_composite(output, (40, 30))
    except Exception as e:
        print(f"Avatar loading error: {e}")
        draw.ellipse([40, 30, 140, 130], fill=(47, 54, 61))

    try:
        font = ImageFont.truetype("arial.ttf", 24)
        title_font = ImageFont.truetype("arial.ttf", 40)
        small_font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    username = interaction.user.name
    draw.text((170, 40), username, font=title_font, fill=text_color)
    draw.line([(170, 90), (550, 90)], fill=accent_color, width=2)

    def draw_rounded_rect_with_border(x, y, w, h, radius, fill_color, border_color, border_width=2):
        draw_rounded_rect(x, y, w, h, radius, fill_color)
        
        for i in range(border_width):
            # Top line
            draw.line([(x + radius, y + i), (x + w - radius, y + i)], fill=border_color)
            # Bottom line
            draw.line([(x + radius, y + h - i - 1), (x + w - radius, y + h - i - 1)], fill=border_color)
            # Left line
            draw.line([(x + i, y + radius), (x + i, y + h - radius)], fill=border_color)
            # Right line
            draw.line([(x + w - i - 1, y + radius), (x + w - i - 1, y + h - radius)], fill=border_color)
        
        # Draw the rounded corners
        for i in range(border_width):
            draw.arc([x + i, y + i, x + radius * 2 - i, y + radius * 2 - i], 180, 270, fill=border_color)
            draw.arc([x + w - radius * 2 + i, y + i, x + w - i, y + radius * 2 - i], 270, 360, fill=border_color)
            draw.arc([x + i, y + h - radius * 2 + i, x + radius * 2 - i, y + h - i], 90, 180, fill=border_color)
            draw.arc([x + w - radius * 2 + i, y + h - radius * 2 + i, x + w - i, y + h - i], 0, 90, fill=border_color)

    # Helper function for basic rounded rectangles
    def draw_rounded_rect(x, y, w, h, radius, color):
        draw.rectangle([x+radius, y, x+w-radius, y+h], fill=color)
        draw.rectangle([x, y+radius, x+w, y+h-radius], fill=color)
        draw.ellipse([x, y, x+radius*2, y+radius*2], fill=color)
        draw.ellipse([x+w-radius*2, y, x+w, y+radius*2], fill=color)
        draw.ellipse([x, y+h-radius*2, x+radius*2, y+h], fill=color)
        draw.ellipse([x+w-radius*2, y+h-radius*2, x+w, y+h], fill=color)
    box_width = 130
    box_height = 55
    box_spacing = 20

    # Helper function to center text in a box
    def get_centered_position(text, box_x, box_width, font):
        text_width = draw.textlength(text, font=font)
        return box_x + (box_width - text_width) / 2

    # Rank box - Centered text
    rank_x = 170
    rank_y = 120
    draw_rounded_rect_with_border(rank_x, rank_y, box_width, box_height, 10, (47, 54, 61), accent_color)
    
    # Center "RANK" text
    rank_label_x = get_centered_position("RANK", rank_x, box_width, small_font)
    draw.text((rank_label_x, rank_y + 5), "RANK", font=small_font, fill=secondary_text_color)
    
    # Center rank number
    rank_number = f"#{level + 1}"
    rank_number_x = get_centered_position(rank_number, rank_x, box_width, font)
    draw.text((rank_number_x, rank_y + 22), rank_number, font=font, fill=text_color)

    # Level box - Centered text
    level_x = rank_x + box_width + box_spacing
    level_y = rank_y
    draw_rounded_rect_with_border(level_x, level_y, box_width, box_height, 10, (47, 54, 61), accent_color)
    
    # Center "LEVEL" text
    level_label_x = get_centered_position("LEVEL", level_x, box_width, small_font)
    draw.text((level_label_x, level_y + 5), "LEVEL", font=small_font, fill=secondary_text_color)
    
    # Center level number
    level_number = str(level)
    level_number_x = get_centered_position(level_number, level_x, box_width, font)
    draw.text((level_number_x, level_y + 22), level_number, font=font, fill=text_color)

    # Progress bar
    bar_width = 380
    bar_height = 30
    bar_x = 170
    bar_y = 220
    
    # Experience text
    draw.text((bar_x, bar_y - 35), "EXPERIENCE", font=small_font, fill=secondary_text_color)
    
    # XP Text
    xp_text = f"{exp}/{next_level_exp} XP"
    text_width = draw.textlength(xp_text, font=small_font)
    draw.text((bar_x + bar_width - text_width, bar_y - 35), xp_text, font=small_font, fill=text_color)
    
    # Background bar
    draw_rounded_rect(bar_x, bar_y, bar_width, bar_height, 15, bar_background)
    
    # Progress bar
    if progress > 0:
        progress_width = int(bar_width * progress)
        if progress_width > 30:
            draw_rounded_rect(bar_x, bar_y, progress_width, bar_height, 15, bar_color)

    # Add corner accents
    corner_size = 20
    accent_color_transparent = (accent_color[0], accent_color[1], accent_color[2], 100)
    
    draw.line([(0, corner_size), (0, 0), (corner_size, 0)], fill=accent_color_transparent, width=2)
    draw.line([(width-corner_size, 0), (width, 0), (width, corner_size)], fill=accent_color_transparent, width=2)
    draw.line([(0, height-corner_size), (0, height), (corner_size, height)], fill=accent_color_transparent, width=2)
    draw.line([(width-corner_size, height), (width, height), (width, height-corner_size)], fill=accent_color_transparent, width=2)

    # Save and send the image
    with io.BytesIO() as image_binary:
        image.save(image_binary, 'PNG')
        image_binary.seek(0)
        file = discord.File(fp=image_binary, filename='level.png')
        
        try:
            await interaction.edit_original_response(content=None, attachments=[file])
        except discord.NotFound:
            try:
                await interaction.followup.send(file=file)
            except:
                pass



def is_admin():
    def predicate(interaction: discord.Interaction):
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)


    
@bot.tree.command(name="delete_ticket", description="This command can only be used in store ticket channels")
@commands.has_permissions(administrator=True)
async def delete_ticket(interaction: discord.Interaction):
    # Check if the channel is a ticket channel
    if not interaction.channel.name.startswith('purchase-'):
        await interaction.response.send_message("This command can only be used in purchase ticket channels!", ephemeral=True)
        return

    # Create confirmation embed
    confirm_embed = discord.Embed(
        title="<a:delete:1336384568260952064> Delete Ticket",
        description="This ticket will be deleted in 5 seconds...",
        color=0xFF0000
    )
    confirm_embed.add_field(
        name="Deleted By",
        value=f"{interaction.user.mention}",
        inline=False
    )

    await interaction.response.send_message(embed=confirm_embed)
    await asyncio.sleep(5)
    await interaction.channel.delete()


@bot.tree.command(name="leaderboard", description="View the top 10 users by experience.")
async def leaderboard(interaction: discord.Interaction):
    sorted_users = sorted(server_data[str(interaction.guild.id)].items(), key=lambda x: x[1]["exp"], reverse=True)[:10]

    embed = discord.Embed(title="🏆 Leaderboard", color=discord.Color.blue())
    for i, (user_id, data) in enumerate(sorted_users, 1):
        user = await bot.fetch_user(int(user_id))
        embed.add_field(
            name=f"{i}. {user.name}",
            value=f"**Level:** {data['level']} | **EXP:** {data['exp']}",
            inline=False
        )

    await interaction.response.send_message(embed=embed)
@bot.tree.command(name="add_lvl", description="Add EXP to a user.")
@commands.has_permissions(administrator=True)
async def add_lvl(interaction: discord.Interaction, user: discord.Member, exp: int):
    user_data = get_user_data(interaction.guild.id, user.id)
    old_level = calculate_level(user_data["exp"])
    user_data["exp"] += exp
    new_level = calculate_level(user_data["exp"])
    user_data["level"] = new_level

    save_data(server_data)
    await interaction.response.send_message(f"✅ {user.mention} has been granted {exp} EXP!")

    if new_level > old_level:
        await interaction.channel.send(f"🎉 {user.mention} leveled up to **Level {new_level}!**")

# Main command implementation
@bot.tree.command(name="addlevel", description="Add experience points to a user")
@app_commands.checks.has_permissions(administrator=True)
async def add_level(
    interaction: discord.Interaction,
    user: discord.Member,
    exp: int
):
    try:
        # Check administrator permissions
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "<a:Animated_Cross:1344705833627549748> You need administrator permissions to use this command!",
                ephemeral=True
            )

        # Defer the response to avoid timeout
        await interaction.response.defer()

        server_id = str(interaction.guild_id)
        user_id = str(user.id)

        # Get current data from data manager
        current_exp = data_manager.get_user_exp(server_id, user_id)
        new_exp = current_exp + exp

        # Calculate new level
        new_level = data_manager.calculate_level(new_exp)

        # Update user data in database
        data_manager.update_exp(server_id, user_id, new_exp)

        # Create success embed
        success_embed = discord.Embed(
            title="<a:animated_tick:1344705804007112724> Experience Added Successfully",
            color=0x2ECC71
        )
        success_embed.add_field(
            name="User",
            value=user.mention,
            inline=False
        )
        success_embed.add_field(
            name="Experience Added",
            value=f"```+{exp} XP```",
            inline=True
        )
        success_embed.add_field(
            name="New Total",
            value=f"```{new_exp} XP```",
            inline=True
        )
        success_embed.add_field(
            name="Current Level",
            value=f"```Level {new_level}```",
            inline=False
        )
        success_embed.set_footer(text=f"Updated by {interaction.user.name}")

        await interaction.followup.send(embed=success_embed)

        # Send DM notification
        try:
            notify_embed = discord.Embed(
                title="🎉 Experience Updated",
                description=f"You received {exp} XP from an administrator!",
                color=0x2ECC71
            )
            notify_embed.add_field(
                name="New Total Experience",
                value=f"{new_exp} XP",
                inline=False
            )
            notify_embed.add_field(
                name="Current Level",
                value=f"Level {new_level}",
                inline=False
            )
            await user.send(embed=notify_embed)
        except discord.Forbidden:
            pass  # Ignore if user has DMs disabled

    except Exception as e:
        error_embed = discord.Embed(
            title="<a:Animated_Cross:1344705833627549748> Error",
            description=f"Failed to update experience: {str(e)}",
            color=0xFF0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)
    
@bot.tree.command(name="spin", description="Spin the wheel of fortune and win rubles!")
async def spin(interaction: discord.Interaction):
    """
    Handle the daily spin command for the Discord bot.
    
    Args:
        interaction (discord.Interaction): The interaction object from the slash command.
    """
    try:
        # Create a context-like object for the interaction
        class Context:
            def __init__(self, interaction):
                self.guild = interaction.guild
                self.author = interaction.user
                self.send = interaction.response.send_message

        ctx = Context(interaction)
        
        # Call the spin_command function from the other file
        # Pass the interaction and client (if needed)
        await spin_command(ctx, bot)
    
    except Exception as e:
        logger.error(f"Error executing spin command: {e}")
        await interaction.response.send_message(
            "An unexpected error occurred while processing your spin. Please try again later.",
            ephemeral=True
        )

@bot.tree.command(
    name="reset",
    description="Reset all data for a specific user!"
)
@app_commands.describe(
    user="The user whose data you want to reset"
)
async def reset(interaction: discord.Interaction, user: discord.User):
    ctx = await bot.get_context(interaction)
    await reset_command(ctx, user, bot)


@bot.tree.command(name="profile_transfer", description="Transfer a user's profile data to another user")
@commands.has_permissions(administrator=True)
async def profile_transfer(
    interaction: discord.Interaction, 
    sender: discord.User, 
    receiver: discord.User
):
    """
    Slash command to transfer user profile data with administrator permissions.
    
    Args:
        interaction (discord.Interaction): The interaction context
        sender (discord.User): The user whose data will be transferred
        receiver (discord.User): The user who will receive the data
    """
    # Create a context-like object for the existing function
    class FakeContext:
        def __init__(self, interaction):
            self.send = interaction.response.send_message
            self.guild = interaction.guild
            self.author = interaction.user

    # Convert interaction to a context-like object
    ctx = FakeContext(interaction)

    # Call the existing profile transfer command
    await profile_transfer_command(ctx, sender, receiver, bot)



@bot.tree.command(name="role", description="Create a custom role!")
@app_commands.describe(
    role_name="Name of the custom role",
    role_color="Hex color code for the role (optional)"
)
async def role_slash_command(
    interaction: discord.Interaction,
    role_name: str,
    role_color: str = None
):
    try:
        await interaction.response.defer(ephemeral=False)
        
        color = discord.Color.blue()
        if role_color:
            try:
                color = discord.Color.from_str(role_color)
            except:
                color = discord.Color.blue()

        approval_view = RoleApprovalView(
            interaction.user, 
            role_name, 
            color
        )
        
        await interaction.followup.send(
            embed=discord.Embed(
                title="🎨 Role Creation Request",
                description="Your role creation request has been sent to administrators for approval.",
                color=color
            )
        )
        
        await approval_view.send_admin_notification(interaction)
        
    except Exception as e:
        await interaction.followup.send("An error occurred.")


@bot.tree.command(name="card_drop", description="Drop a random Genshin Impact card for users to claim")
async def card_drop(interaction: discord.Interaction):
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(embed=discord.Embed(
            title="<a:Animated_Cross:1344705833627549748> Permission Denied",
            description="You need administrator permissions to use this command.",
            color=discord.Color.red()
        ), ephemeral=True)
        return

    try:
        # Randomly select a card
        card = random.choice(GENSHIN_CARDS)
        
        # Create the initial drop embed
        embed = discord.Embed(
            title="🎴 Rare Card Drop!",
            description="A rare Genshin Impact card has appeared!\nClick the button below to claim it!",
            color=discord.Color.blue()
        )
        embed.add_field(name="Card Name", value=card['name'])
        embed.add_field(name="Rarity", value=card['rarity'])
        embed.set_image(url=card['image'])
        
        # Create and send the view with the embed
        view = CardDropView(card)
        await interaction.response.send_message(embed=embed, view=view)
        
        # Wait for the view to timeout
        await view.wait()
        
        # If no one claimed the card
        if not view.claimed_by:
            timeout_embed = discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Card Expired",
                description="No one claimed the card in time!",
                color=discord.Color.red()
            )
            await interaction.channel.send(embed=timeout_embed)

    except Exception as e:
        error_embed = discord.Embed(
            title="<a:Animated_Cross:1344705833627549748> Error",
            description="An error occurred while dropping the card.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        print(f"Error in card drop command: {e}")
    
@bot.tree.command(name="bounty", description="Set up a new bounty with a reward!!")
@app_commands.describe(
    reward="Amount of rubles for the bounty reward", 
    image_url="Optional URL for bounty image"
)
async def bounty(interaction: discord.Interaction, reward: int, image_url: Optional[str] = None):
    try:
        await interaction.response.defer()
        
        class InteractionContext:
            def __init__(self, interaction):
                self.interaction = interaction
                self.author = interaction.user
                self.guild = interaction.guild
                self.send = self._send
                self.message = None

            async def _send(self, *args, **kwargs):
                if kwargs.get('ephemeral', False):
                    return await self.interaction.followup.send(*args, **kwargs)
                else:
                    self.message = await self.interaction.followup.send(*args, **kwargs)
                    return self.message

            async def update_member_count(self):
                while True:
                    try:
                        if self.message and hasattr(self.message, 'embeds') and len(self.message.embeds) > 0:
                            embed = self.message.embeds[0]
                            description = embed.description
                            
                            from games.bounty import global_bounty_event
                            participant_role = self.guild.get_role(global_bounty_event.participant_role_id)
                            if participant_role:
                                global_bounty_event.participant_count = len(participant_role.members)
                                
                            lines = description.split('\n')
                            for i, line in enumerate(lines):
                                if "Eligible Players" in line:
                                    lines[i] = f"**Eligible Players**: {global_bounty_event.participant_count}"
                            
                            embed.description = '\n'.join(lines)
                            await self.message.edit(embed=embed)
                            
                        await asyncio.sleep(5)  
                        
                    except Exception as e:
                        logger.error(f"Error updating member count: {e}")
                        break

        ctx = InteractionContext(interaction)
        await bounty_command(ctx, reward, image_url)
        asyncio.create_task(ctx.update_member_count())
    except BountyCommandError as bounty_error:
        await interaction.followup.send(
            f"<a:Animated_Cross:1344705833627549748> {str(bounty_error)}", 
            ephemeral=True
        )
        logger.error(f"Bounty error: {bounty_error}")
    except Exception as e:
        await interaction.followup.send(
            "<a:Animated_Cross:1344705833627549748> An unexpected error occurred", 
            ephemeral=True
        )
        logger.error(f"Unexpected error in bounty command: {e}", exc_info=True)

@bot.tree.command(name="pull", description="Try your luck with bounty pulls")
@app_commands.describe(amount="Number of pulls")
@app_commands.choices(amount=[
    app_commands.Choice(name="Single Pull (160 Rubles)", value=1),
    app_commands.Choice(name="Multi Pull (1600 Rubles)", value=10)
])
async def pull(interaction: discord.Interaction, amount: int = 1):
    user_data = get_user_data(interaction.guild.id, interaction.user.id)
    cost_per_pull = 160
    total_cost = cost_per_pull * amount

    if user_data["currency"] < total_cost:
        await interaction.response.send_message("❌ You don't have enough rubles to pull!", ephemeral=True)
        return

    update_rubles(interaction.guild.id, interaction.user.id, -total_cost)

    win_chance = 0.02  # 2% chance to win
    won = any(random.random() < win_chance for _ in range(amount))

    if won:
        reward = 6000
        update_rubles(interaction.guild.id, interaction.user.id, reward)
        await interaction.response.send_message(f"🎉 {interaction.user.mention} won the bounty and received **{reward} rubles!**")
    else:
        await interaction.response.send_message("❌ No bounty won this time. Better luck next time!")

@bot.tree.command(name="rr", description="Start a Russian Roulette game")
async def rr_start(interaction: discord.Interaction, entry_fee: int = 100):
    if not interaction.guild or not interaction.channel:
        await interaction.response.send_message("This command can only be used in a server.")
        return

    if entry_fee <= 0:
        await interaction.response.send_message("Entry fee must be greater than 0 rubles.")
        return

    # Initialize game manager if it doesn't exist
    if not hasattr(bot, 'game_manager'):
        bot.game_manager = GameManager()
    
    # Check if there's an active game
    if bot.game_manager.current_game and bot.game_manager.current_game.is_active:
        await interaction.response.send_message("A game is currently in progress! Please wait for it to finish.")
        return
    
    # Create or get game
    game = bot.game_manager.create_new_game(entry_fee)
    view = RouletteView(game, bot.game_manager)
    
    embed = view.create_game_embed()
    await interaction.response.send_message(embed=embed, view=view)


colors = [discord.Color.blue(), discord.Color.purple(), discord.Color.green(), discord.Color.yellow(), discord.Color.red()]

TRACKED_CHANNEL_IDS = [1327334550883405997, 1318804968085651559, 1327337715208818779, 1330798363138064395]  # Replace with actual channel IDs

@bot.tree.command(name="daily", description="Check your daily commission progress")
async def daily(interaction):
    await handle_commission(interaction, "daily")

@bot.tree.command(name="weekly", description="Check your weekly commission progress")
async def weekly(interaction):
    await handle_commission(interaction, "weekly")

async def handle_commission(interaction, commission_type):
    try:
        user_data = get_user_data(interaction.guild.id, interaction.user.id)
        current_time = datetime.now(timezone.utc)
        embed = discord.Embed(color=random.choice(colors))
        
        last_reset_key = f"last_{commission_type}_reset"
        msg_key = f"{commission_type}_messages"
        rewards_key = f"{commission_type}_rewards_claimed"
        
        if commission_type == "daily":
            last_reset = datetime.fromtimestamp(user_data.get(last_reset_key, 0), tz=timezone.utc)
            duration = timedelta(days=1)
            msg_count = user_data.get(msg_key, 0)
            claimed_rewards = user_data.get(rewards_key, [])
            tiers = {100: 50, 200: 75, 350: 100, 400: 150, 500: 175, 700: 200, 1000: 300}
            embed.title = "Daily Commissions"
        else:
            last_reset = datetime.fromtimestamp(user_data.get(last_reset_key, 0), tz=timezone.utc)
            duration = timedelta(weeks=1)
            msg_count = user_data.get(msg_key, 0)
            claimed_weekly = user_data.get(rewards_key, False)
            tiers = {9000: 1600}
            embed.title = "Weekly Commissions"

        if current_time - last_reset >= duration:
            user_data[msg_key] = 0
            user_data[rewards_key] = [] if commission_type == "daily" else False
            user_data[last_reset_key] = current_time.timestamp()

        progress_text = ""
        for msg_target, reward in tiers.items():
            is_claimed = (str(msg_target) in claimed_rewards if commission_type == "daily" else claimed_weekly)
            progress = min(msg_count / msg_target * 100, 100)
            filled_blocks = int(progress // 10)
            progress_bar = "█" * filled_blocks
            if filled_blocks < 10:
                partial = progress % 10
                progress_bar += "░" if partial < 3.33 else "▒" if partial < 6.66 else "▓"
                progress_bar += "░" * (9 - filled_blocks)
            
            if msg_count >= msg_target and not is_claimed:
                user_data["currency"] += reward
                if commission_type == "daily":
                    claimed_rewards.append(str(msg_target))
                else:
                    user_data["weekly_reward_claimed"] = True
                status = "COMPLETED!"
                progress_line = f"```ansi\n\u001b[32m{progress_bar}\u001b[0m```"
                # Send a message in the chat pinging the user about the reward
                await interaction.channel.send(
                    f"{interaction.user.mention} has completed the {commission_type} commission and earned {reward} <a:Rubles:1344705820222292011>"
                )
            elif is_claimed:
                status = "Claimed"
                progress_line = f"```ansi\n\u001b[36m{progress_bar}\u001b[0m```"
            else:
                status = f"{progress:.1f}%"
                progress_line = f"```ansi\n\u001b[33m{progress_bar}\u001b[0m```"

            progress_text += f"{msg_target} msgs → {reward} <a:Rubles:1344705820222292011>\n{progress_line}{status}\n"

        embed.description = progress_text
        embed.add_field(name="Messages Sent", value=f"{msg_count} messages", inline=True)

        next_reset = last_reset + duration
        time_left = (next_reset - current_time).total_seconds()
        if commission_type == "daily":
            time_remaining = f"Resets in {int(time_left // 3600)}h {int((time_left % 3600) // 60)}m"
        else:
            days = int(time_left // 86400)
            hours_remaining = int((time_left % 86400) // 3600)
            time_remaining = f"Resets in {days}d {hours_remaining}h"
            
        embed.add_field(name="Time Remaining", value=time_remaining, inline=True)

        save_data(server_data)
        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Error",
                description=f"An error occurred: {str(e)}",
                color=random.choice(colors)
            ),
            ephemeral=True
        )

@bot.event
async def on_message(message):
    if message.channel.id in TRACKED_CHANNEL_IDS and not message.author.bot:
        user_data = get_user_data(message.guild.id, message.author.id)
        user_data["daily_messages"] = user_data.get("daily_messages", 0) + 1
        user_data["weekly_messages"] = user_data.get("weekly_messages", 0) + 1
        save_data(server_data)
    await bot.process_commands(message)

@bot.tree.command(name="mines", description="Play Mines!")
@app_commands.describe(
    bet="Amount to bet",
    mines="Number of mines (1-5)"
)
async def mines(
    interaction: Interaction,
    bet: app_commands.Range[int, MIN_BET, MAX_BET],
    mines: app_commands.Range[int, MIN_MINES, MAX_MINES] = 3
):
    await play_mines(interaction, bet, mines)


@bot.tree.command(name="setupstore", description="Set up a store in the current channel")
@app_commands.checks.has_permissions(administrator=True)
async def setup_store(interaction: discord.Interaction):
    try:
        # Ensure the interaction is valid before proceeding
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)  # Acknowledge the interaction immediately

        # Create the store
        store = await store_manager.create_store(interaction.channel)
        
        # Send a follow-up message
        await interaction.followup.send("<a:animated_tick:1344705804007112724> Store has been successfully set up in this channel!", ephemeral=True)
    except discord.NotFound as e:
        await interaction.followup.send(f"<a:Animated_Cross:1344705833627549748> Error: Interaction not found or expired. Please try again.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"<a:Animated_Cross:1344705833627549748> Error setting up store: {e}", ephemeral=True)
        
@bot.tree.command(name="additem", description="Add an item to the store")
@app_commands.describe(
    name="The name of the item",
    price="The price in Rubles",
    stock="The amount of items available",
    emoji="The emoji to associate with the item (optional)"
)
@app_commands.checks.has_permissions(administrator=True)
async def add_item(interaction: discord.Interaction, name: str, price: int, stock: int, emoji: str = None):
    try:
        store = store_manager.get_store(str(interaction.channel_id))
        if not store:
            await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> No store found in this channel. Use `/setupstore` first!", ephemeral=True)
            return

        item_data = {
            "value": price,
            "stock": stock
        }

        if emoji:
            item_data["emoji"] = emoji

        store.store[name] = item_data
        store._save_store_data()
        await store.update_store_display()
        await interaction.response.send_message(f"<a:animated_tick:1344705804007112724> Added item '{name}' to the store! {emoji if emoji else ''}")
    except Exception as e:
        await interaction.response.send_message(f"<a:Animated_Cross:1344705833627549748> Error adding item: {e}", ephemeral=True)

@bot.tree.command(name="removeitem", description="Remove an item from the store")
@app_commands.describe(name="The name of the item to remove")
@app_commands.checks.has_permissions(administrator=True)
async def remove_item(interaction: discord.Interaction, name: str):
    try:
        store = store_manager.get_store(str(interaction.channel_id))
        if not store:
            await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> No store found in this channel!", ephemeral=True)
            return

        if name in store.store:
            del store.store[name]
            store._save_store_data()
            await store.update_store_display()
            await interaction.response.send_message(f"<a:animated_tick:1344705804007112724> Removed item '{name}' from the store!")
        else:
            await interaction.response.send_message(f"<a:Animated_Cross:1344705833627549748> Item '{name}' not found in the store!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"<a:Animated_Cross:1344705833627549748> Error removing item: {e}", ephemeral=True)

@bot.tree.command(name="updatestock", description="Update the stock of an item")
@app_commands.describe(
    name="The name of the item",
    stock="The new stock amount"
)
@app_commands.checks.has_permissions(administrator=True)
async def update_stock(interaction: discord.Interaction, name: str, stock: int):
    try:
        store = store_manager.get_store(str(interaction.channel_id))
        if not store:
            await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> No store found in this channel!", ephemeral=True)
            return

        if name in store.store:
            store.store[name]['stock'] = stock
            store._save_store_data()
            await store.update_store_display()
            await interaction.response.send_message(f"<a:animated_tick:1344705804007112724> Updated stock for '{name}' to {stock}!")
        else:
            await interaction.response.send_message(f"<a:Animated_Cross:1344705833627549748> Item '{name}' not found in the store!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"<a:Animated_Cross:1344705833627549748> Error updating stock: {e}", ephemeral=True)

@bot.tree.command(name="updateprice", description="Update the price of an item")
@app_commands.describe(
    name="The name of the item",
    price="The new price in Rubles"
)
@app_commands.checks.has_permissions(administrator=True)
async def update_price(interaction: discord.Interaction, name: str, price: int):
    try:
        store = store_manager.get_store(str(interaction.channel_id))
        if not store:
            await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> No store found in this channel!", ephemeral=True)
            return

        if name in store.store:
            store.store[name]['value'] = price
            store._save_store_data()
            await store.update_store_display()
            await interaction.response.send_message(f"<a:animated_tick:1344705804007112724> Updated price for '{name}' to {price} Rubles!")
        else:
            await interaction.response.send_message(f"<a:Animated_Cross:1344705833627549748> Item '{name}' not found in the store!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"<a:Animated_Cross:1344705833627549748> Error updating price: {e}", ephemeral=True)

@bot.tree.command(name="removestore", description="Remove the store from the current channel")
@app_commands.checks.has_permissions(administrator=True)
async def remove_store(interaction: discord.Interaction):
    try:
        await store_manager.remove_store(str(interaction.channel_id))
        await interaction.response.send_message("<a:animated_tick:1344705804007112724> Store has been removed from this channel!")
    except Exception as e:
        await interaction.response.send_message(f"<a:Animated_Cross:1344705833627549748> Error removing store: {e}", ephemeral=True)

@bot.tree.command(name="store", description="View the store in the current channel")
@app_commands.checks.has_permissions(administrator=True)
async def view_store(interaction: discord.Interaction):
    try:
        store = store_manager.get_store(str(interaction.channel_id))
        if not store:
            await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> No store found in this channel!", ephemeral=True)
            return

        await store.update_store_display()
        await interaction.response.send_message("<a:animated_tick:1344705804007112724> Store display updated!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"<a:Animated_Cross:1344705833627549748> Error displaying store: {e}", ephemeral=True)


@bot.tree.command(name="battle", description="Test the Battle Royale system")
@app_commands.checks.has_permissions(administrator=True)
async def battle(interaction: discord.Interaction):
    """Test command to check if Battle Royale is working properly"""
    try:
        await start_battle_royale(interaction.channel)
        await interaction.response.send_message("<a:animated_tick:1344705804007112724> Battle Royale test started!", ephemeral=True)
    except discord.app_commands.errors.MissingPermissions:
        await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> You need administrator permissions to use this command!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"<a:Animated_Cross:1344705833627549748> Error testing Battle Royale: {e}", ephemeral=True)

@bot.tree.command(
    name="testttt", 
    description="Test the Tic Tac Toe game functionality (Admin only)"
)
async def test_ttt(interaction: discord.Interaction):
    try:
        # Check if user has admin role
        if not any(role.permissions.administrator for role in interaction.user.roles):
            error_embed = discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Error",
                description="You need administrator permissions to use this command!",
                color=0xe74c3c
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        await interaction.response.defer()
        await start_tictactoe(interaction.channel)
        await interaction.followup.send("<a:animated_tick:1344705804007112724> Tic Tac Toe test started!", ephemeral=True)
        
    except Exception as e:
        error_embed = discord.Embed(
            title="<a:Animated_Cross:1344705833627549748> Error", 
            description=f"An error occurred while testing: {str(e)}",
            color=0xe74c3c
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)


@bot.tree.command(
    name="participant",
    description="Create a participant role assignment button (Admin only)"
)
@app_commands.describe(
    role="The role to assign to participants",
    duration="How long the button should remain active (in minutes)"
)
@discord.app_commands.checks.has_permissions(administrator=True)
async def participant(interaction: discord.Interaction, role: discord.Role, duration: int = 60):
    try:
        # Verify role matches bounty participant role ID
        from games.bounty import global_bounty_event
        if role.id != global_bounty_event.participant_role_id:
            await interaction.response.send_message(
                f"<a:Animated_Cross:1344705833627549748> This command only works with the designated bounty participant role <@&{global_bounty_event.participant_role_id}>",
                ephemeral=True
            )
            return

        # Create embed for role assignment
        embed = discord.Embed(
            title="🎮 Bounty Event Participant Role",
            description=(
                f"Click below to get the {role.mention} role!\n\n"
                "**Benefits:**\n"
                "• Participate in bounty events\n"
                "• Earn rewards through pulls\n" 
                "• Compete for massive prize pools\n\n"
                "**Note:** Only users with this role can participate in bounty events!\n\n"
                f"⏰ This button will be active for {duration} minutes!"
            ),
            color=discord.Color.blue()
        )

        # Create view with button
        class RoleButton(discord.ui.View):
            def __init__(self, role: discord.Role):
                super().__init__(timeout=duration * 60)  # Convert minutes to seconds
                self.role = role
                self.message = None  # Initialize message attribute

            @discord.ui.button(label="Get Role", style=discord.ButtonStyle.green, emoji="✨")
            async def button_callback(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                user = button_interaction.user
                
                if self.role in user.roles:
                    await button_interaction.response.send_message(
                        f"You already have the {self.role.name} role!", 
                        ephemeral=True
                    )
                else:
                    try:
                        await user.add_roles(self.role)
                        
                        # Update participant count in bounty event
                        if global_bounty_event.active:
                            global_bounty_event.participant_count += 1
                            
                        await button_interaction.response.send_message(
                            f"<a:animated_tick:1344705804007112724> Role granted! You can now participate in bounty events.", 
                            ephemeral=True
                        )
                    except discord.Forbidden:
                        await button_interaction.response.send_message(
                            "<a:Animated_Cross:1344705833627549748> I don't have permission to assign that role!", 
                            ephemeral=True
                        )

            async def on_timeout(self):
                # Disable the button when timeout occurs
                for child in self.children:
                    child.disabled = True
                
                # Get the message and update it
                if self.message:
                    embed = self.message.embeds[0]
                    embed.description += "\n\n**⏰ This button has expired!**"
                    await self.message.edit(embed=embed, view=self)

        view = RoleButton(role)
        response = await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()  # Store message reference

    except discord.app_commands.errors.MissingPermissions:
        await interaction.response.send_message(
            "<a:Animated_Cross:1344705833627549748> You need administrator permissions to use this command!", 
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"<a:Animated_Cross:1344705833627549748> An error occurred: {str(e)}", 
            ephemeral=True
        )

async def remove_participant_roles():
    """Remove participant roles from all users after bounty ends"""
    try:
        from games.bounty import global_bounty_event
        
        # Only proceed if there was an active bounty that just ended
        if not global_bounty_event.active and global_bounty_event.participants:
            
            # Get all guilds the bot is in
            for guild in bot.guilds:
                # Get the participant role for this guild
                participant_role = guild.get_role(global_bounty_event.participant_role_id)
                
                if participant_role:
                    # Remove role from all members who have it
                    for member in participant_role.members:
                        try:
                            await member.remove_roles(participant_role)
                            logger.info(f"Removed participant role from {member.name} in {guild.name}")
                        except discord.Forbidden:
                            logger.error(f"Failed to remove role from {member.name} - Missing Permissions")
                        except Exception as e:
                            logger.error(f"Error removing role from {member.name}: {e}")
                            
                    # Reset participant tracking
                    global_bounty_event.participants.clear()
                    global_bounty_event.participant_count = 0
                    
    except Exception as e:
        logger.error(f"Error in remove_participant_roles: {e}")

# Modify the bounty_command to call role removal when event ends
original_bounty_command = bounty_command

async def bounty_command_wrapper(*args, **kwargs):
    await original_bounty_command(*args, **kwargs)
    
    # Check if event ended and remove roles
    from games.bounty import global_bounty_event
    if not global_bounty_event.active:
        await remove_participant_roles()

# Replace original command with wrapped version        
bounty_command = bounty_command_wrapper

# Modify pulls_command to check for role removal after win
original_pulls_command = pulls_command 

async def pulls_command_wrapper(*args, **kwargs):
    await original_pulls_command(*args, **kwargs)
    
    # Check if event ended from a win and remove roles
    from games.bounty import global_bounty_event
    if not global_bounty_event.active:
        await remove_participant_roles()

# Replace original command with wrapped version
pulls_command = pulls_command_wrapper


@bot.tree.command(name="globalreset", description="Reset all user data for the server (Admin only)")
@app_commands.default_permissions(administrator=True)
async def globalreset_command(interaction: discord.Interaction):
    """
    Command to reset all user data for the server.
    Only administrators can use this command.
    """
    try:
        ctx = SimpleNamespace()
        ctx.guild = interaction.guild
        ctx.author = interaction.user
        ctx.send = interaction.response.send_message
        await global_reset_command(ctx, bot)

    except Exception as e:
        error_embed = discord.Embed(
            title="<a:Animated_Cross:1344705833627549748> Error",
            description=f"An error occurred while processing the command: {str(e)}",
            color=discord.Color.red()
        )
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=error_embed, ephemeral=True)


@bot.tree.command(name="tictactoe", description="Challenge another user to Tic Tac Toe")
@app_commands.describe(
    opponent="The user you want to challenge",
    bet_amount="Amount to bet (10-2000 rubles)"
)
async def tictactoe_command(
    interaction: discord.Interaction,
    opponent: discord.Member,
    bet_amount: int = 100
):
    """
    Command to start a Tic Tac Toe game with another user
    """
    try:
        # Validate bet amount
        if bet_amount < MIN_BET:
            await interaction.response.send_message(
                f"<a:Animated_Cross:1344705833627549748> Minimum bet is {MIN_BET} <a:Rubles:1344705820222292011>!",
                ephemeral=True
            )
            return
            
        if bet_amount > MAX_BET:
            await interaction.response.send_message(
                f"<a:Animated_Cross:1344705833627549748> Maximum bet is {MAX_BET} <a:Rubles:1344705820222292011>!",
                ephemeral=True
            )
            return

        # Check if challenging self
        if opponent.id == interaction.user.id:
            await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> You cannot challenge yourself!", ephemeral=True)
            return

        # Check if opponent is a bot
        if opponent.bot:
            await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> You cannot challenge a bot!", ephemeral=True)
            return

        # Check challenger's balance
        challenger_balance = get_user_rubles(str(interaction.guild_id), str(interaction.user.id))
        if challenger_balance < bet_amount:
            await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> You don't have enough rubles to place this bet!", ephemeral=True)
            return

        # Check opponent's balance
        opponent_balance = get_user_rubles(str(interaction.guild_id), str(opponent.id))
        if opponent_balance < bet_amount:
            await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> Your opponent doesn't have enough rubles to match this bet!", ephemeral=True)
            return

        # Deduct bets from both players
        update_rubles(str(interaction.guild_id), str(interaction.user.id), -bet_amount)
        update_rubles(str(interaction.guild_id), str(opponent.id), -bet_amount)

        # Add players to active games
        active_games[interaction.user.id] = True
        active_games[opponent.id] = True

        view = TicTacToeView(interaction.user, opponent, bet_amount)
        
        embed = discord.Embed(
            title="🎮 Tic Tac Toe",
            description=f"Game started between {interaction.user.mention} and {opponent.mention}\n"
                       f"Bet amount: {bet_amount} <a:Rubles:1344705820222292011>\n\n"
                       f"It's {interaction.user.mention}'s turn!",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(
            content=f"{interaction.user.mention} vs {opponent.mention}",
            embed=embed,
            view=view
        )

    except Exception as e:
        error_embed = discord.Embed(
            title="<a:Animated_Cross:1344705833627549748> Error",
            description=f"An error occurred: {str(e)}",
            color=discord.Color.red()
        )
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=error_embed, ephemeral=True)


@bot.tree.command(name="slots", description="Play the slot machine! Bet between 10-2000 rubles")
@app_commands.describe(bet="Amount to bet (10-2000 rubles)")
async def slots_command(interaction: Interaction, bet: int):
    global game_running
    if 'game_running' in globals() and game_running:
        await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> A game is already running. Please wait for it to finish!", ephemeral=True)
        return

    game_running = True

    try:
        await play_slots(interaction, bet)
    finally:
        game_running = False


@bot.tree.command(
    name="crash",
    description="🚀 Play the crash game - cash out before it crashes! (Max bet: 1500)"
)
@app_commands.describe(
    bet="Amount of rubles to bet (1-2000)"
)
async def crash_command(interaction: discord.Interaction, bet: int):
    if bet <= 0:
        await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> Bet amount must be positive!", ephemeral=True)
        return

    # Check if a crash game is already running
    global crash_game_running
    if 'crash_game_running' in globals() and crash_game_running:
        await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> A game is already running. Please wait for it to finish!", ephemeral=True)
        return

    crash_game_running = True

    try:
        await play_crash(interaction, bet)
    except Exception as e:
        error_embed = discord.Embed(
            title="<a:Animated_Cross:1344705833627549748> Error",
            description=f"An error occurred: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
    finally:
        crash_game_running = False


@bot.tree.command(name="blackjack", description="Play a game of blackjack!")
@app_commands.describe(bet="Amount to bet (10-1000 rubles)")
async def blackjack_command(interaction: Interaction, bet: int):
    global blackjack_game_running
    if 'blackjack_game_running' in globals() and blackjack_game_running:
        await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> A blackjack game is already running. Please wait for it to finish!", ephemeral=True)
        return

    blackjack_game_running = True

    try:
        await play_blackjack(interaction, bet)
    finally:
        blackjack_game_running = False

@bot.tree.command(name="plinko", description="Play Plinko!")
@app_commands.describe(
    bet="Amount to bet",
    risk="Risk level (low, medium, high)"
)
@app_commands.choices(risk=[
    app_commands.Choice(name="Low Risk", value="low"),
    app_commands.Choice(name="Medium Risk", value="medium"),
    app_commands.Choice(name="High Risk", value="high")
])
async def plinko(
    interaction: Interaction,
    bet: app_commands.Range[int, MIN_BET, MAX_BET],
    risk: str = "medium"
):
    global game_running
    if 'game_running' in globals() and game_running:
        await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> A game is already running. Please wait for it to finish!", ephemeral=True)
        return

    game_running = True

    try:
        await play_plinko(interaction, bet, risk)
    finally:
        game_running = False

@bot.tree.command(name="ping", description="Check if the bot is responsive")
async def ping_command(interaction: Interaction):
    latency = bot.latency * 1000  # Convert to milliseconds
    embed = discord.Embed(
        title="Pong! 🏓",
        description=f"Bot latency: {latency:.2f} ms",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="8ball", description="Ask the magic 8-ball a question")
@app_commands.describe(
    question="The question you want to ask the magic 8-ball",
    private="Choose whether the response should be private (default) or public"
)
async def eight_ball_command(interaction: Interaction, question: str, private: bool = True):
    responses = [
        "It is certain.",
        "It is decidedly so.",
        "Without a doubt.",
        "Yes – definitely.",
        "You may rely on it.",
        "As I see it, yes.",
        "Most likely.",
        "Outlook good.",
        "Yes.",
        "Signs point to yes.",
        "Reply hazy, try again.",
        "Ask again later.",
        "Better not tell you now.",
        "Cannot predict now.",
        "Concentrate and ask again.",
        "Don't count on it.",
        "My reply is no.",
        "My sources say no.",
        "Outlook not so good.",
        "Very doubtful."
    ]
    
    if not question.strip():
        await interaction.response.send_message(
            "<a:Animated_Cross:1344705833627549748> You must ask a question!",
            ephemeral=True
        )
        return

    response = random.choice(responses)
    embed = discord.Embed(
        title="🎱 The Magic 8-Ball says...",
        description=response,
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, ephemeral=private)


@bot.tree.command(name="dm", description="Send a direct message to a specific person or multiple people")
@app_commands.describe(
    user_ids="The IDs of the users you want to DM, separated by commas",
    message="The message you want to send"
)
async def dm_command(interaction: discord.Interaction, user_ids: str, message: str):
    # Define the role ID that is allowed to use this command
    allowed_role_id = 1329091841576140841

    # Check if the user has the required role
    if allowed_role_id not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message(
            "<a:Animated_Cross:1344705833627549748> You do not have permission to use this command.",
            ephemeral=True
        )
        return

    user_ids_list = user_ids.split(",")
    failed_users = []
    for user_id in user_ids_list:
        try:
            user = await bot.fetch_user(int(user_id.strip()))
            if user:
                await user.send(message)
        except Exception as e:
            failed_users.append(user_id.strip())

    if failed_users:
        await interaction.response.send_message(
            f"<a:Animated_Cross:1344705833627549748> Failed to send message to the following user IDs: {', '.join(failed_users)}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "<a:animated_tick:1344705804007112724> Message sent successfully!",
            ephemeral=True
        )

@bot.tree.command(name="invites", description="Check how many users you've invited")
async def invites_command(interaction: discord.Interaction):
    server_id = interaction.guild_id
    user_id = interaction.user.id
    
    user_data = get_user_data(server_id, user_id)
    total_invites = user_data.get("total_invites", 0)
    active_invites = user_data.get("active_invites", 0)
    claimed_rewards = user_data.get("claimed_rewards", 0)
    
    claimable_invites = total_invites - claimed_rewards
    claimable_amount = claimable_invites * 50  # 50 rubles per invite
    
    # Create simplified embed
    embed = discord.Embed(
        title="🎟️ Invite Statistics",
        color=discord.Color.purple()
    )
    
    embed.add_field(name="Total Invites", value=f"{total_invites}", inline=True)
    embed.add_field(name="Active Invites", value=f"{active_invites}", inline=True)
    embed.add_field(name="Reward Rate", value=f"50 <a:Rubles:1344705820222292011> rubles per invite", inline=False)
    
    if claimable_invites > 0:
        embed.add_field(
            name="Claimable", 
            value=f"{claimable_amount} <a:Rubles:1344705820222292011> ({claimable_invites} invites)",
            inline=False
        )
    
    # Create button for the embed
    class InviteButtons(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
        
        @discord.ui.button(label="Claim Rewards", style=discord.ButtonStyle.green, disabled=claimable_invites <= 0)
        async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if claimable_invites <= 0:
                await interaction.response.send_message("You have no rewards to claim.", ephemeral=True)
                return
            
            # Process the claim
            user_data["claimed_rewards"] = claimed_rewards + claimable_invites
            save_data(server_data)  # Assuming you have this function
            
            await interaction.response.send_message(
                f"You've claimed {claimable_amount} rubles for your {claimable_invites} invites!",
                ephemeral=True
            )
            
            # Update the original embed to reflect the claim
            updated_embed = discord.Embed(
                title="Invite Statistics",
                color=discord.Color.blue()
            )
            
            updated_embed.add_field(name="Total Invites", value=f"{total_invites}", inline=True)
            updated_embed.add_field(name="Active Invites", value=f"{active_invites}", inline=True)
            updated_embed.add_field(name="Reward Rate", value=f"50 rubles per invite", inline=False)
            updated_embed.add_field(
                name="Claimable",
                value="0 rubles (all claimed)",
                inline=False
            )
            
            # Disable the button after claiming
            self.children[0].disabled = True
            await interaction.message.edit(embed=updated_embed, view=self)
    
    # Send the embed with button
    await interaction.response.send_message(embed=embed, view=InviteButtons()) 








bot.run(BOT_TOKEN)