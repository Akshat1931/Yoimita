import random
import logging
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from data_manager import get_user_data, update_last_spin, update_rubles



# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class SpinCommandError(Exception):
    """Custom exception for spin command-related errors."""
    pass

async def spin_command(ctx, client):
    """
    Handle the daily spin command with robust error handling and enhanced features.
    
    Args:
        ctx (discord.Context): The context of the command invocation
        client (discord.Client): The Discord bot client
    
    Raises:
        SpinCommandError: For various potential error scenarios
    """
    try:
        # Validate input parameters
        if not ctx or not ctx.guild or not ctx.author:
            raise SpinCommandError("Invalid command context")

        server_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)
        
        # Advanced Reward Tiers with Weighted Probabilities
        REWARD_TIERS = [
            {"amount": 10, "probability": 0.40},  # 40% chance
            {"amount": 20, "probability": 0.25},  # 25% chance
            {"amount": 30, "probability": 0.15},  # 15% chance
            {"amount": 50, "probability": 0.10},  # 10% chance
            {"amount": 70, "probability": 0.05},  # 5% chance
            {"amount": 100, "probability": 0.05}  # 5% chance
        ]
        
        # Retrieve user data with enhanced error handling
        try:
            user_data = get_user_data(server_id, user_id)
        except Exception as data_error:
            logger.error(f"Data retrieval error for user {user_id}: {data_error}")
            raise SpinCommandError("Could not retrieve user data")
        
        # Validate last spin time with more robust datetime handling
        current_time = datetime.now()
        last_spin_time = user_data.get('last_spin')
        
        if last_spin_time:
            try:
                last_spin = datetime.fromisoformat(last_spin_time)
                if last_spin.date() == current_time.date():
                    await ctx.send(f"{ctx.author.mention}, you've already spun today! Try again tomorrow.")
                    return
            except ValueError:
                logger.warning(f"Invalid last spin time format for user {user_id}")
        
        # Weighted random reward selection
        reward = random.choices(
            [tier["amount"] for tier in REWARD_TIERS],
            weights=[tier["probability"] for tier in REWARD_TIERS]
        )[0]
        
        # Update user's currency and last spin time
        try:
            update_rubles(server_id, user_id, reward)
            update_last_spin(server_id, user_id, current_time.isoformat())
        except Exception as update_error:
            logger.error(f"Error updating user data: {update_error}")
            raise SpinCommandError("Failed to update user spin data")
        
        # Enhanced Embed with Dynamic Color and More Information
        reward_color = discord.Color.green()
        if reward >= 70:
            reward_color = discord.Color.gold()  # Gold for higher rewards
        elif reward <= 20:
            reward_color = discord.Color.light_grey()  # Grey for lower rewards
        
        embed = discord.Embed(
            title="🎰 Wheel of Fortune!", 
            description=f"{ctx.author.mention} gave the wheel a spin!", 
            color=reward_color
        )
        embed.add_field(name="✨ Reward", value=f"<a:Rubles:1344705820222292011> {reward} Rubles", inline=False)
        
        # Add probability context for fun
        tier = next(tier for tier in REWARD_TIERS if tier["amount"] == reward)
        embed.add_field(
            name="🍀 Luck Factor", 
            value=f"You beat the {tier['probability']*100:.0f}% odds!", 
            inline=False
        )
        
        embed.set_footer(text="Daily spin resets at midnight. Good luck!")
        
        # Log successful spin
        logger.info(f"User {user_id} spun and won {reward} rubles")
        
        await ctx.send(embed=embed)
    
    except SpinCommandError as spin_error:
        # Centralized error handling
        await ctx.send(f"<a:Animated_Cross:1344705833627549748> Spin Error: {spin_error}")
        logger.error(f"Spin command error: {spin_error}")
    except Exception as unexpected_error:
        # Catch-all for unexpected errors
        await ctx.send("An unexpected error occurred during your spin. Please try again later.")
        logger.error(f"Unexpected spin error: {unexpected_error}", exc_info=True)

