import random
import asyncio
import discord
from data_manager import server_data, get_user_data, save_data

async def play_guess_the_number(channel):
    """A simple number guessing game using Discord embeds."""
    try:
        # Generate random number and send initial message
        number = random.randint(1, 10)
        print(f"DEBUG: Number to guess is {number}")
        
        # Create starting embed
        start_embed = discord.Embed(
            title="🎲 Guess the Number!",
            description="Pick a number between 1 and 10. You have 20 seconds!",
            color=0x3498db  # Blue color
        )
        start_embed.set_footer(text="Type your guess in the chat!")
        await channel.send(embed=start_embed)

        # Get bot instance more reliably
        bot = channel.guild.me._state._get_client()
        
        guessed_users = set()
        
        def check(msg):
            return (
                msg.channel.id == channel.id and
                not msg.author.bot and
                any(char.isdigit() for char in msg.content)
            )

        end_time = asyncio.get_event_loop().time() + 20
        while asyncio.get_event_loop().time() < end_time:
            try:
                remaining_time = max(0.1, end_time - asyncio.get_event_loop().time())
                msg = await bot.wait_for('message', check=check, timeout=remaining_time)
                
                # Extract all numbers from the message
                numbers = [int(num) for num in ''.join(char if char.isdigit() else ' ' for char in msg.content).split()]
                if not numbers:
                    continue
                    
                # Process each number in the message
                for guess in numbers:
                    if not 1 <= guess <= 10:
                        continue
                        
                    user = msg.author
                    print(f"DEBUG: Processing guess {guess} from {user.name}")
                    
                    if guess == number:
                        # Correct guess embed
                        winner_embed = discord.Embed(
                            title="🎉 WINNER!",
                            description=f"Congratulations {user.name}!\nYou correctly guessed the number {number}!",
                            color=0x2ecc71  # Green color
                        )
                        winner_embed.add_field(
                            name="Prize",
                            value="You win 50 <a:Rubles:1344705820222292011>!",
                            inline=False
                        )
                        await channel.send(embed=winner_embed)
                        
                        # Award currency
                        user_data = get_user_data(str(channel.guild.id), str(user.id))
                        user_data["currency"] += 50
                        save_data(server_data)
                        return
                    else:
                        # Wrong guess - fixed description logic
                        guess_state = "HIGH" if guess > number else "LOW"
                        direction = "lower" if guess > number else "higher"
                        
                        wrong_embed = discord.Embed(
                            title="<a:Animated_Cross:1344705833627549748> Wrong Number!",
                            description=f"{user.mention}, your guess of **{guess}** is too {guess_state}!\nTry a {direction} number!",
                            color=0xff0000  # Red color
                        )
                        wrong_embed.set_footer(text="Keep trying! 🎲")
                        await channel.send(embed=wrong_embed)
                        
                        # Add to guessed users set
                        guessed_users.add(user.id)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"DEBUG: Error processing guess: {e}")
                continue
        
        # Time's up embed
        timeout_embed = discord.Embed(
            title="⌛ Time's up!",
            description=f"The number was **{number}**!",
            color=0x95a5a6  # Gray color
        )
        
        guessed_users_mentions = [f"<@{uid}>" for uid in guessed_users]
        if guessed_users_mentions:
            players = ", ".join(guessed_users_mentions)
            timeout_embed.add_field(
                name="Thanks for playing!",
                value=players,
                inline=False
            )
        else:
            timeout_embed.add_field(
                name="Participants",
                value="Nobody tried to guess 😢",
                inline=False
            )
            
        await channel.send(embed=timeout_embed)
        
    except Exception as e:
        print(f"DEBUG: Game error: {e}")
        error_embed = discord.Embed(
            title="<a:Animated_Cross:1344705833627549748> Error",
            description="An error occurred in the game. Please try again.",
            color=0xff0000  # Red color
        )
        try:
            await channel.send(embed=error_embed)
        except:
            pass