import random
from typing import Dict, Optional
import discord
import asyncio
from discord.ui import Button, View
from data_manager import server_data, get_user_data, save_data

class CoinFlipView(View):
    def __init__(self, original_message: discord.Message, bet_amount: int):
        super().__init__(timeout=30)
        self.players: Dict[int, dict] = {}
        self.original_message = original_message
        self.countdown_task: Optional[asyncio.Task] = None
        self.bet_amount = min(bet_amount, 2000)
        
        heads_button = Button(
            style=discord.ButtonStyle.primary,
            label="Heads (1.19x)",
            emoji="👑",
            custom_id="heads"
        )
        heads_button.callback = self.heads_callback
        
        tails_button = Button(
            style=discord.ButtonStyle.primary,
            label="Tails (1.09x)",
            emoji="🔄",
            custom_id="tails"
        )
        tails_button.callback = self.tails_callback
        
        self.add_item(heads_button)
        self.add_item(tails_button)
    
    def create_embed(self, seconds_left: int) -> discord.Embed:
        multiplier_text = (
            "**Multipliers:**\n"
            "👑 Heads: 1.19x your bet\n"
            "🔄 Tails: 1.09x your bet"
        )
        
        return discord.Embed(
            title="🎲 Enhanced Coin Flip Game!",
            description=(
                f"⏰ **{seconds_left} seconds remaining!**\n\n"
                f"Bet {self.bet_amount} <a:Rubles:1344705820222292011> to play!\n\n"
                f"{multiplier_text}\n\n"
                f"Current Players: {len(self.players)}"
            ),
            color=0xf1c40f
        ).set_footer(text="Maximum bet: 2000 rubles")
    
    async def start_countdown(self):
        try:
            for seconds_left in range(30, -1, -1):
                embed = self.create_embed(seconds_left)
                await self.original_message.edit(embed=embed)
                await asyncio.sleep(1)
        except Exception as e:
            print(f"Coin flip countdown error: {str(e)}")
            raise
    
    async def heads_callback(self, interaction: discord.Interaction):
        await self.handle_choice(interaction, "heads")
        
    async def tails_callback(self, interaction: discord.Interaction):
        await self.handle_choice(interaction, "tails")
        
    async def handle_choice(self, interaction: discord.Interaction, choice: str):
        if not interaction.user:
            await interaction.response.send_message(
                "Error: Could not identify user.",
                ephemeral=True
            )
            return

        user_id = interaction.user.id
        
        # Verify user has enough rubles
        user_data = get_user_data(str(interaction.guild.id), str(user_id))
        if user_data["rubles"] < self.bet_amount:
            await interaction.response.send_message(
                f"You need {self.bet_amount} rubles to play! You have {user_data['rubles']} rubles.",
                ephemeral=True
            )
            return
        
        if user_id in self.players:
            await interaction.response.send_message(
                "You've already placed your bet!", 
                ephemeral=True
            )
            return
            
        self.players[user_id] = {
            'user': interaction.user,
            'choice': choice
        }
        
        multiplier = 1.19 if choice == "heads" else 1.09
        potential_win = int(self.bet_amount * multiplier)
        
        await interaction.response.send_message(
            f"You chose {choice.title()}! Potential win: {potential_win} rubles", 
            ephemeral=True
        )

    def calculate_reward(self, choice: str, won: bool) -> int:
        if not won:
            return -self.bet_amount
            
        multiplier = 1.19 if choice == "heads" else 1.09
        return int(self.bet_amount * multiplier)

async def play_coinflip(channel: discord.TextChannel, bet_amount: int = 50):
    """
    An enhanced multi-player coin flip game with different multipliers for heads and tails.
    
    Args:
        channel (discord.TextChannel): The channel to play the game in
        bet_amount (int): Amount of rubles to bet (default: 50, max: 2000)
    """
    try:
        # Validate bet amount
        if bet_amount <= 0:
            await channel.send(embed=discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Invalid Bet",
                description="Bet amount must be greater than 0 rubles.",
                color=0xff0000
            ))
            return
            
        if bet_amount > 2000:
            await channel.send(embed=discord.Embed(
                title="<a:Warning:1334552043863543878> Bet Amount Adjusted",
                description="Maximum bet is 2000 rubles. Bet has been adjusted.",
                color=0xf39c12
            ))
            bet_amount = 2000

        # Create and send initial game message
        initial_embed = discord.Embed(
            title="🎲 Enhanced Coin Flip Game!",
            description=(
                "⏰ **30 seconds remaining!**\n\n"
                f"Bet {bet_amount} <a:Rubles:1344705820222292011> to play!\n\n"
                "**Multipliers:**\n"
                "👑 Heads: 1.19x your bet\n"
                "🔄 Tails: 1.09x your bet\n\n"
                "Current Players: 0"
            ),
            color=0xf1c40f
        ).set_footer(text="Maximum bet: 2000 rubles")
        
        message = await channel.send(embed=initial_embed)
        view = CoinFlipView(message, bet_amount)
        await message.edit(view=view)
        
        # Handle game countdown
        view.countdown_task = asyncio.create_task(view.start_countdown())
        await view.wait()
        
        if view.countdown_task and not view.countdown_task.done():
            view.countdown_task.cancel()
        
        if not view.players:
            await message.edit(
                embed=discord.Embed(
                    title="⌛ Time's up!",
                    description="Nobody joined the game!",
                    color=0x95a5a6
                ),
                view=None
            )
            return
            
        # Determine game result
        coin_result = random.choice(["heads", "tails"])
        
        result_embed = discord.Embed(
            title="🎲 Coin Flip Results!",
            color=0x3498db
        ).add_field(
            name="The coin shows...",
            value=f"**{coin_result.upper()}!**" + (" 👑" if coin_result == "heads" else " 🔄"),
            inline=False
        )
        
        # Process results
        winners = []
        losers = []
        total_payout = 0
        
        try:
            for player_id, player_data in view.players.items():
                user = player_data['user']
                choice = player_data['choice']
                won = choice == coin_result
                reward = view.calculate_reward(choice, won)
                
                user_data = get_user_data(str(channel.guild.id), str(player_id))
                user_data["rubles"] += reward
                total_payout += reward
                
                if won:
                    winners.append((user.mention, reward))
                else:
                    losers.append((user.mention, abs(reward)))
            
            save_data(server_data)
            
        except Exception as e:
            print(f"Error processing rewards: {str(e)}")
            raise
        
        # Add results to embed
        if winners:
            winners_text = "\n".join([f"🎉 {winner} (+{reward} rubles)" for winner, reward in winners])
            result_embed.add_field(
                name="🏆 Winners",
                value=winners_text,
                inline=False
            )
        
        if losers:
            losers_text = "\n".join([f"😢 {loser} (-{amount} rubles)" for loser, amount in losers])
            result_embed.add_field(
                name="💸 Better Luck Next Time",
                value=losers_text,
                inline=False
            )
        
        # Add game statistics
        result_embed.add_field(
            name="Game Stats",
            value=(
                f"Total Players: {len(view.players)}\n"
                f"Winners: {len(winners)}\n"
                f"Losers: {len(losers)}\n"
                f"Net Payout: {total_payout:+} rubles"
            ),
            inline=False
        )
        
        await message.edit(embed=result_embed, view=None)
        
    except Exception as e:
        print(f"Coin flip game error: {str(e)}")
        error_embed = discord.Embed(
            title="<a:Animated_Cross:1344705833627549748> Error",
            description="An error occurred in the game. Please try again.",
            color=0xff0000
        )
        await channel.send(embed=error_embed)