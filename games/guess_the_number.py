# games/guess_the_number.py

import random
import asyncio
import discord
from __main__ import server_data, get_user_data, save_data

async def play_guess_the_number(channel):
    """A simple number guessing game."""
    number = random.randint(1, 10)
    await channel.send("🎲 Let's play 'Guess the Number'! Pick a number between 1 and 10.")
    
    def check(msg):
        # Make sure we only accept responses in the same channel and verify they're numbers
        return msg.channel == channel and msg.content.isdigit() and 1 <= int(msg.content) <= 10
    
    try:
        msg = await channel.guild.fetch_channel(channel.id)
        msg = await msg.guild.bot.wait_for("message", check=check, timeout=30)
        guess = int(msg.content)
        
        if guess == number:
            await channel.send(f"🎉 Congratulations {msg.author.mention}! The number was {number}. You win 100 <a:rubles:1329009278811373740>!")
            # Get user data and add currency
            server_id = str(channel.guild.id)
            user_id = str(msg.author.id)
            user_data = get_user_data(server_id, user_id)
            user_data["currency"] += 100
            save_data(server_data)
        else:
            await channel.send(f"❌ Sorry {msg.author.mention}, the number was {number}. Better luck next time!")
    except asyncio.TimeoutError:
        await channel.send("⌛ Time's up! No one guessed the number.")