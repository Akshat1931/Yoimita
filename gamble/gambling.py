import random
from discord import Embed, Color
from data_manager import get_user_rubles, server_data, get_user_data, save_data, update_rubles
import discord
import asyncio
from typing import List, Tuple
from discord import Interaction
active_games = {}

async def play_coinflip(interaction, bet: int, choice: str):
    try:
        # Bet limit check
        MAX_BET = 2000
        if bet > MAX_BET:
            await interaction.response.send_message(f"<a:Animated_Cross:1344705833627549748> Maximum bet is {MAX_BET} rubles!", ephemeral=True)
            return

        user = get_user_data(interaction.guild.id, interaction.user.id)
        if user["currency"] < bet:
            await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> Insufficient funds!", ephemeral=True)
            return

        # Adjusted multipliers for a slight loss on losing
        win_multiplier = 1.99
        loss_multiplier = 0.9  # Lose a little more than the bet

        # Use a random choice for the coin flip with equal probability
        result = random.choice(["heads", "tails", "edge"])
        
        if result == "edge":
            # It's a tie, no currency change
            embed = Embed(
                title="<a:coins:1334760494149402666> Coin Flip Tie!",
                color=Color.gold(),
                description=f"**Flip:** {result.upper()} | **Choice:** {choice.upper()}\n"
                            f"**Result:** It's a tie! No rubles lost or won."
            )
        else:
            won = choice.lower() == result

            if won:
                winnings = int(bet * win_multiplier)
                user["currency"] += (winnings - bet)
                
                embed = Embed(
                    title="<a:coins:1344705813205487792> Coin Flip Winner!",
                    color=Color.green(),
                    description=f"**Flip:** {result.upper()} | **Choice:** {choice.upper()}\n"
                              f"**Multi:** {win_multiplier:.2f}x\n"
                              f"**Won:** {winnings} <a:Rubles:1344705820222292011>"
                )
            else:
                # Deduct a bit more than the bet amount
                loss_amount = int(bet * loss_multiplier)
                user["currency"] -= loss_amount
                
                embed = Embed(
                    title="<a:coins:1344705813205487792> Coin Flip Loss!",
                    color=Color.red(),
                    description=f"**Flip:** {result.upper()} | **Choice:** {choice.upper()}\n"
                              f"**Lost:** {loss_amount} <a:Rubles:1344705820222292011>"
                )

        embed.add_field(
            name="Balance",
            value=f"{user['currency']} <a:Rubles:1344705820222292011>"
        )
        embed.set_footer(text=f"Win Multiplier: {win_multiplier:.2f}x | Loss Multiplier: {loss_multiplier:.2f}x")
        
        save_data(server_data)
        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(
            f"<a:loading_icon:1334757784834674700> Error: {str(e)}", 
            ephemeral=True
        )


        
async def play_colorwheel(interaction, bet: int, color: str):
    try:
        # Check if user already has an active game
        if interaction.user.id in active_games:
            await interaction.response.send_message(
                "<a:Animated_Cross:1344705833627549748> You already have an active game! Please finish it before starting a new one.",
                ephemeral=True
            )
            return

        # Add the game to active games
        active_games[interaction.user.id] = "colorwheel"

        # Bet limit check
        MAX_BET = 2000
        if bet > MAX_BET:
            await interaction.response.send_message(
                f"<a:Animated_Cross:1344705833627549748> Maximum bet is {MAX_BET} rubles!",
                ephemeral=True
            )
            if interaction.user.id in active_games:
                del active_games[interaction.user.id]
            return

        user = get_user_data(interaction.guild.id, interaction.user.id)
        if user["currency"] < bet:
            await interaction.response.send_message(
                "<a:Animated_Cross:1344705833627549748> Insufficient funds!",
                ephemeral=True
            )
            if interaction.user.id in active_games:
                del active_games[interaction.user.id]
            return

        # Updated color wheel multipliers with lower values
        color_multipliers = {
            "green": 3.0,  
            "red": 2.0,    
            "black": 1.12   # Updated from 1.0 to 1.12
        }

        # Spin wheel
        result = random.choices(
            ["green", "red", "black"],
            weights=[1, 6.2, 6.2]
        )[0]

        won = color.lower() == result
        multiplier = color_multipliers[color.lower()]

        if won:
            winnings = int(bet * multiplier)
            user["currency"] += (winnings - bet)
            
            embed = Embed(title="🎡 COLOR WHEEL WINNER!", color=Color.green())
            embed.add_field(
                name="Spin Result",
                value=f"• Landed on: **{result.upper()}**\n🎯 Your choice: **{color.upper()}**"
            )
            embed.add_field(
                name="Rewards",
                value=(
                    f"• Multiplier: **{multiplier:.2f}x**\n"
                    f"• Winnings: **{winnings}** <a:Rubles:1344705820222292011>"
                )
            )
        else:
            user["currency"] -= bet
            
            embed = Embed(title="🎡 COLOR WHEEL LOSS!", color=Color.red())
            embed.add_field(
                name="Spin Result",
                value=f"• Landed on: **{result.upper()}**\n🎯 Your choice: **{color.upper()}**"
            )
            embed.add_field(
                name="Loss",
                value=f"• Lost: **{bet}** <a:Rubles:1344705820222292011>"
            )

        embed.add_field(
            name="Balance",
            value=f"• New Balance: **{user['currency']}** <a:Rubles:1344705820222292011>"
        )
        embed.set_footer(text="Green: 3x | Red: 2x | Black: 1.12x")  # Updated footer text to reflect new black multiplier
        
        save_data(server_data)
        await interaction.response.send_message(embed=embed)

        # Clean up active game after successful completion
        if interaction.user.id in active_games:
            del active_games[interaction.user.id]

    except Exception as e:
        # Clean up on error
        if interaction.user.id in active_games:
            del active_games[interaction.user.id]
            
        await interaction.response.send_message(
            f"<a:Animated_Cross:1344705833627549748> An error occurred: {str(e)}",
            ephemeral=True
        )


#-----------------------------------------------------------------------------------------------------------------


import random
from typing import List, Tuple
import discord
import asyncio
from discord import Interaction

class SlotsGame:
    """Slot machine with multiple paylines and features"""
    
    SYMBOLS = {
        "7️⃣": {"value": 3, "weight": 1},     # Jackpot (rare)
        "💎": {"value": 2.5, "weight": 2},     # Diamond (very valuable)
        "🎰": {"value": 2, "weight": 3},     # BAR (high value)
        "🍒": {"value": 1.5, "weight": 4},     # Cherry (medium value)
        "🍋": {"value": 1.2, "weight": 5},   # Lemon (low value)
        "⭐": {"value": 1, "weight": 6}      # Star (common value)
    }
    
    FEATURES = {
        "🃏": {"name": "Wild", "desc": "Substitutes any symbol"},
        "💫": {"name": "Scatter", "desc": "Triggers free spins"},
        "🎲": {"name": "Bonus", "desc": "Triggers bonus game"}
    }
    
    GRID_SIZE = (3, 5)  # 3 rows, 5 columns
    
    PAYLINES = [
        [(1,0), (1,1), (1,2), (1,3), (1,4)],  # Middle horizontal
        [(0,0), (0,1), (0,2), (0,3), (0,4)],  # Top horizontal
        [(2,0), (2,1), (2,2), (2,3), (2,4)],  # Bottom horizontal
        [(0,0), (1,1), (2,2), (1,3), (0,4)],  # V shape
        [(2,0), (1,1), (0,2), (1,3), (2,4)],  # Inverted V
        [(1,0), (0,1), (0,2), (0,3), (1,4)],  # Top zigzag
        [(1,0), (2,1), (2,2), (2,3), (1,4)],  # Bottom zigzag
        [(0,0), (1,0), (2,0), (1,1), (0,2)],  # Left diagonal
        [(2,0), (1,1), (0,2), (1,3), (2,4)]   # Right diagonal
    ]

    def __init__(self):
        self.grid = [[None for _ in range(self.GRID_SIZE[1])] for _ in range(self.GRID_SIZE[0])]
        
    def _get_weighted_symbol(self) -> str:
        """Get a random symbol based on weights"""
        symbols = []
        weights = []
        
        for symbol, data in self.SYMBOLS.items():
            symbols.append(symbol)
            weights.append(data["weight"])
            
        return random.choices(symbols, weights=weights, k=1)[0]

    def spin(self) -> List[List[str]]:
        """Spin the slot machine and return the grid"""
        for i in range(self.GRID_SIZE[0]):
            for j in range(self.GRID_SIZE[1]):
                self.grid[i][j] = self._get_weighted_symbol()
        return self.grid

    def check_paylines(self) -> List[Tuple[int, List[Tuple[int, int]], str]]:
        """Check all paylines for wins and return (multiplier, positions, symbol)"""
        wins = []
        
        for payline in self.PAYLINES:
            symbols = [self.grid[r][c] for r, c in payline]
            first_symbol = symbols[0]
            
            # Check if we have a win (3 or more matching symbols)
            match_count = 1
            matched_positions = [payline[0]]
            
            for i in range(1, len(symbols)):
                if symbols[i] == first_symbol or symbols[i] == "🃏":  # Include wild symbol
                    match_count += 1
                    matched_positions.append(payline[i])
                else:
                    break
                    
            if match_count >= 3:  # Need at least 3 matching symbols
                # Random multiplier based on match count and symbol value
                base_multiplier = self.SYMBOLS[first_symbol]["value"]
                random_bonus = random.uniform(0.3, 1.0)  # Random bonus between 0.3x and 1.0x
                multiplier = base_multiplier * (match_count - 2) * random_bonus
                wins.append((multiplier, matched_positions, first_symbol))
                
        return wins

async def play_slots(interaction: Interaction, bet: int):
    """Play the slot machine game"""
    try:
        # Check if bet is valid
        if bet < 10:
            await interaction.response.send_message("Minimum bet is 10 rubles!", ephemeral=True)
            return
        
        # Add maximum bet limit
        if bet > 2000:
            await interaction.response.send_message("Maximum bet is 2000 rubles!", ephemeral=True)
            return
            
        # Check user balance
        user_balance = get_user_rubles(str(interaction.guild_id), str(interaction.user.id))
        if user_balance < bet:
            await interaction.response.send_message("Insufficient balance!", ephemeral=True)
            return

        # Create game instance
        game = SlotsGame()
        
        # Create initial embed
        embed = discord.Embed(
            title="🎰 Slots Machine",
            description="Spinning...",
            color=discord.Color.dark_purple()
        )
        embed.add_field(name="Bet", value=f"{bet} rubles")
        
        # Send initial message
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        
        # Spinning animation
        for _ in range(3):
            game.spin()
            grid_display = "\n".join([" ".join(row) for row in game.grid])
            embed.description = f"```\n{grid_display}\n```"
            await message.edit(embed=embed)
            await asyncio.sleep(0.5)
        
        # Final spin
        final_grid = game.spin()
        wins = game.check_paylines()
        
        # Calculate total winnings
        total_winnings = 0
        win_descriptions = []
        
        for multiplier, positions, symbol in wins:
            win_amount = int(bet * multiplier)  # Convert to integer to avoid floating point
            total_winnings += win_amount
            positions_str = " → ".join([f"({r+1},{c+1})" for r, c in positions])
            win_descriptions.append(f"{symbol} x{len(positions)}: {win_amount} rubles ({positions_str})")
        
        # Deduct bet and add winnings
        update_rubles(str(interaction.guild_id), str(interaction.user.id), -bet)  # Deduct bet
        if total_winnings > 0:
            update_rubles(str(interaction.guild_id), str(interaction.user.id), total_winnings)
        
        # Create result embed
        result_embed = discord.Embed(
            title="🎰 Slots Result",
            color=discord.Color.green() if total_winnings > 0 else discord.Color.red()
        )
        
        # Display final grid
        grid_display = "\n".join([" ".join(row) for row in final_grid])
        result_embed.description = f"```\n{grid_display}\n```"
        
        # Add bet and result fields
        result_embed.add_field(name="Bet", value=f"{bet} rubles", inline=True)
        result_embed.add_field(
            name="Result", 
            value=f"{'Won' if total_winnings > 0 else 'Lost'} {total_winnings if total_winnings > 0 else bet} rubles",
            inline=True
        )
        
        # Add winning paylines if any
        if win_descriptions:
            result_embed.add_field(
                name="Winning Lines", 
                value="\n".join(win_descriptions),
                inline=False
            )
        
        # Add new balance
        new_balance = get_user_rubles(str(interaction.guild_id), str(interaction.user.id))
        result_embed.add_field(
            name="New Balance",
            value=f"{new_balance} rubles",
            inline=False
        )
        
        # Update message with final result
        await message.edit(embed=result_embed)
        
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



class CrashGame:
    def __init__(self):
        self.multiplier = 1.0
        self.is_crashed = False
        self.crash_value = self._generate_crash_value()
        self.volatility = random.uniform(0.5, 1.5)  # Reduced upper volatility limit
        
    def _generate_crash_value(self) -> float:
        rand = random.random()
        
        # Increased chances of early crashes
        if random.random() < 0.20:  
            return random.uniform(1.01, 1.15)  # Slightly lower early crash range
            
        # More aggressive probability distribution
        if rand < 0.8:  # 80% chance
            return random.uniform(1.1, 1.6)  # Lower normal range
        elif rand < 0.95:  # 15% chance
            return random.uniform(1.6, 2.0)  # Lower medium range
        else:  # 5% chance
            return random.uniform(2.0, 5.0)  # Reduced max multiplier
    
    def get_current_multiplier(self) -> float:
        return round(self.multiplier, 2)
    
    def tick(self) -> bool:
        if self.multiplier >= self.crash_value:
            self.is_crashed = True
            return False
        
        # More volatile multiplier increases
        # Base increase is affected by current volatility
        base_increase = random.uniform(0.01, 0.05)  # Reduced base increase range
        
        # Random volatility spikes
        if random.random() < 0.1:  # 10% chance of volatile movement
            self.volatility = random.uniform(0.2, 2.0)  # Reduced upper volatility spike limit
        
        # Apply volatility to multiplier increase
        self.multiplier += base_increase * self.volatility
        
        # Random instant crash chance increases with multiplier
        instant_crash_chance = (self.multiplier - 1.0) * 0.05  # 5% increased chance per 1.0x
        if random.random() < instant_crash_chance:
            self.is_crashed = True
            return False
            
        return True

async def play_crash(interaction: Interaction, bet: int):
    try:
        MAX_BET = 2000
        if bet > MAX_BET:
            await interaction.response.send_message(f"<a:Animated_Cross:1344705833627549748> Maximum bet is {MAX_BET} rubles!", ephemeral=True)
            return

        user = get_user_data(interaction.guild.id, interaction.user.id)
        if user["currency"] < bet:
            await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> Insufficient funds!", ephemeral=True)
            return

        game = CrashGame()
        
        def create_game_embed(multiplier: float, status: str = "LIVE", winnings: int = 0):
            if status == "LIVE":
                color = Color.blue()
                title = "🚀 CRASH GAME"
                description = "The rocket is flying! Cash out before it explodes! 💥"
            elif status == "CRASHED":
                color = Color.red()
                title = "💥 CRASHED!"
                description = f"Crashed at {multiplier:.2f}x! Better luck next time! 🎲"
            else:  # CASHED_OUT
                color = Color.green()
                title = "<a:Rubles:1344705820222292011> SUCCESSFUL CASH OUT!"
                profit = winnings - bet
                description = f"""
🎯 **Perfect Timing!**
                
<a:Rubles:1344705820222292011> Initial Bet: {bet:,} rubles
📈 Multiplier: {multiplier:.2f}x
<a:Rubles:1344705820222292011> Total Winnings: {winnings:,} rubles
📊 Profit: +{profit:,} rubles
                
🌟 Well played! Keep up the great strategy! 🎉
"""

            embed = Embed(title=title, description=description, color=color)
            
            if status != "CASHED_OUT":
                embed.add_field(name="<a:Rubles:1344705820222292011> Bet", value=f"{bet:,} rubles", inline=True)
                embed.add_field(name="📈 Multiplier", value=f"{multiplier:.2f}x", inline=True)
                
                # More detailed progress visualization
                progress = "▓" * int(min(multiplier * 2, 10)) + "░" * (10 - int(min(multiplier * 2, 10)))
                embed.add_field(name="Progress", value=f"`{progress}`", inline=False)
            
            if status == "LIVE":
                embed.set_footer(text=".React down to cash out!")
            elif status == "CASHED_OUT":
                embed.set_footer(text="🎮 Thanks for playing!")
            elif status == "CRASHED":
                embed.set_footer(text="💣 The rocket exploded!")
            
            return embed
        
        msg = await interaction.response.send_message(embed=create_game_embed(game.get_current_multiplier()))
        message = await interaction.original_response()
        await message.add_reaction("<a:Rubles:1344705820222292011>")
        
        def check(reaction, user):
            return user == interaction.user and str(reaction.emoji) == "<a:Rubles:1344705820222292011>"
        
        while True:
            try:
                if not game.tick():
                    await message.edit(embed=create_game_embed(game.get_current_multiplier(), "CRASHED"))
                    update_rubles(interaction.guild.id, interaction.user.id, -bet)
                    break
                
                await message.edit(embed=create_game_embed(game.get_current_multiplier()))
                
                try:
                    await interaction.client.wait_for('reaction_add', timeout=0.5, check=check)
                    winnings = int(bet * game.get_current_multiplier())
                    await message.edit(embed=create_game_embed(game.get_current_multiplier(), "CASHED_OUT", winnings))
                    update_rubles(interaction.guild.id, interaction.user.id, winnings - bet)
                    break
                except asyncio.TimeoutError:
                    continue
                
            except Exception as e:
                print(f"Error in crash game: {e}")
                break
                
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
