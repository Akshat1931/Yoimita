import random
import discord
import asyncio
from discord.ui import Button, View
from data_manager import server_data, get_user_data, save_data

class CoinFlipView(View):
    def __init__(self, original_message):
        super().__init__(timeout=30)
        self.players = {}
        self.original_message = original_message
        self.countdown_task = None
        
        # Add Heads button
        heads_button = Button(
            style=discord.ButtonStyle.primary,
            label="Heads",
            emoji="👑",
            custom_id="heads"
        )
        heads_button.callback = self.heads_callback
        
        # Add Tails button
        tails_button = Button(
            style=discord.ButtonStyle.primary,
            label="Tails",
            emoji="🔄",
            custom_id="tails"
        )
        tails_button.callback = self.tails_callback
        
        self.add_item(heads_button)
        self.add_item(tails_button)
    
    def create_embed(self, seconds_left):
        return discord.Embed(
            title="🎲 Group Coin Flip Game!",
            description=(
                f"⏰ **{seconds_left} seconds remaining!**\n\n"
                "Bet 50 <a:rubles:1329009278811373740> on Heads or Tails!\n\n"
                "Winners get 50 coins, losers lose 50 coins.\n"
                f"Current Players: {len(self.players)}"
            ),
            color=0xf1c40f  # Gold color
        ).set_footer(text="Click a button to join the game!")
    
    async def start_countdown(self):
        try:
            for seconds_left in range(30, -1, -1):
                embed = self.create_embed(seconds_left)
                await self.original_message.edit(embed=embed)
                await asyncio.sleep(1)
        except Exception as e:
            print(f"DEBUG: Countdown error: {e}")
    
    async def heads_callback(self, interaction: discord.Interaction):
        await self.handle_choice(interaction, "heads")
        
    async def tails_callback(self, interaction: discord.Interaction):
        await self.handle_choice(interaction, "tails")
        
    async def handle_choice(self, interaction: discord.Interaction, choice: str):
        user_id = interaction.user.id
        
        # Check if user already made a choice
        if user_id in self.players:
            await interaction.response.send_message(
                "You've already placed your bet!", 
                ephemeral=True
            )
            return
            
        # Store user's choice
        self.players[user_id] = {
            'user': interaction.user,
            'choice': choice
        }
        
        await interaction.response.send_message(
            f"You chose {choice.title()}! Wait for results...", 
            ephemeral=True
        )

async def play_coinflip(channel):
    """A multi-player coin flip game where users bet on heads or tails."""
    try:
        # Create initial embed
        initial_embed = discord.Embed(
            title="🎲 Group Coin Flip Game!",
            description=(
                "⏰ **30 seconds remaining!**\n\n"
                "Bet 50 <a:rubles:1329009278811373740> on Heads or Tails!\n\n"
                "Winners get 50 coins, losers lose 50 coins.\n"
                "Current Players: 0"
            ),
            color=0xf1c40f  # Gold color
        )
        initial_embed.set_footer(text="Click a button to join the game!")
        
        # Send initial message
        message = await channel.send(embed=initial_embed)
        
        # Create view with reference to message
        view = CoinFlipView(message)
        await message.edit(view=view)
        
        # Start countdown task
        view.countdown_task = asyncio.create_task(view.start_countdown())
        
        # Wait for timeout
        await view.wait()
        
        # Cancel countdown task if it's still running
        if view.countdown_task and not view.countdown_task.done():
            view.countdown_task.cancel()
        
        # If no one played
        if not view.players:
            timeout_embed = discord.Embed(
                title="⌛ Time's up!",
                description="Nobody wanted to flip the coin!",
                color=0x95a5a6  # Gray color
            )
            await message.edit(embed=timeout_embed, view=None)
            return
            
        # Flip the coin
        coin_result = random.choice(["heads", "tails"])
        
        # Create result embed
        result_embed = discord.Embed(
            title="🎲 Coin Flip Results!",
            color=0x3498db  # Blue color
        )
        
        # Add coin result
        result_embed.add_field(
            name="The coin shows...",
            value=f"**{coin_result.upper()}!**" + (" 👑" if coin_result == "heads" else " 🔄"),
            inline=False
        )
        
        # Process all players
        winners = []
        losers = []
        
        for player_id, player_data in view.players.items():
            user = player_data['user']
            choice = player_data['choice']
            user_data = get_user_data(str(channel.guild.id), str(player_id))
            
            if choice == coin_result:
                winners.append(user.mention)
                user_data["currency"] += 50
            else:
                losers.append(user.mention)
                user_data["currency"] -= 50
        
        # Add winners section
        if winners:
            winners_text = "\n".join([f"🎉 {winner} (+50 coins)" for winner in winners])
            result_embed.add_field(
                name="🏆 Winners",
                value=winners_text,
                inline=False
            )
        
        # Add losers section
        if losers:
            losers_text = "\n".join([f"😢 {loser} (-50 coins)" for loser in losers])
            result_embed.add_field(
                name="💸 Better Luck Next Time",
                value=losers_text,
                inline=False
            )
        
        # Save all currency changes
        save_data(server_data)
        
        # Show game stats
        result_embed.add_field(
            name="Game Stats",
            value=(
                f"Total Players: {len(view.players)}\n"
                f"Winners: {len(winners)}\n"
                f"Losers: {len(losers)}"
            ),
            inline=False
        )
        
        # Update message with results
        await message.edit(embed=result_embed, view=None)
        
    except Exception as e:
        print(f"DEBUG: Game error: {e}")
        error_embed = discord.Embed(
            title="❌ Error",
            description="An error occurred in the game. Please try again.",
            color=0xff0000  # Red color
        )
        try:
            await channel.send(embed=error_embed)
        except:
            pass