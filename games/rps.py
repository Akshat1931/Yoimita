import discord
import random
import asyncio
from discord.ext import commands, tasks
from data_manager import get_user_data, save_data, server_data

bot = commands.Bot


class RPSView(discord.ui.View):
    def __init__(self, timeout):
        super().__init__(timeout=timeout)
        self.players = {}
        self.done_event = asyncio.Event()
        self.timed_out = False

    @discord.ui.select(
        placeholder="Choose your move!",
        options=[
            discord.SelectOption(label="Rock", emoji="👊", value="rock"),
            discord.SelectOption(label="Paper", emoji="📄", value="paper"),
            discord.SelectOption(label="Scissors", emoji="✂️", value="scissors"),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select):
        if interaction.user.id in self.players:
            await interaction.response.send_message("You've already played!", ephemeral=True)
            return
        
        self.players[interaction.user.id] = {
            'user': interaction.user,
            'move': interaction.data['values'][0]
        }
        
        await interaction.response.send_message(
            f"You selected {interaction.data['values'][0]}!", ephemeral=True
        )
        
        if len(self.players) >= 2:
            self.done_event.set()
            self.stop()

    async def on_timeout(self):
        self.timed_out = True
        self.done_event.set()
        await super().on_timeout()

async def play_rps(channel):
    """A rock paper scissors game using dropdown menus."""
    try:
        game_embed = discord.Embed(
            title="🎮 Rock Paper Scissors Time!",
            description=(
                "First two players to choose their moves will play!\n\n"
                "Use the dropdown below to select your move.\n"
                "You have 30 seconds to play!"
            ),
            color=0x9b59b6
        )
        game_embed.set_footer(text="Game will start when two players make their moves!")
        
        view = RPSView(timeout=30)
        message = await channel.send(embed=game_embed, view=view)
        
        await view.done_event.wait()
        
        # Disable the view after game ends
        await message.edit(view=None)
        
        players = view.players
        if len(players) < 2:
            timeout_embed = discord.Embed(
                title="⌛ Time's up!",
                description="Not enough players joined the game!",
                color=0x95a5a6
            )
            if players:
                players_list = ", ".join([f"<@{pid}>" for pid in players.keys()])
                timeout_embed.add_field(
                    name="Thanks for playing!",
                    value=players_list,
                    inline=False
                )
            await channel.send(embed=timeout_embed)
            return
        
        move_mapping = {
            'rock': '👊 Rock',
            'paper': '📄 Paper',
            'scissors': '✂️ Scissors'
        }
        player_ids = list(players.keys())
        player1 = players[player_ids[0]]
        player2 = players[player_ids[1]]
        p1_move = player1['move']
        p2_move = player2['move']
        
        winner = None
        if p1_move == p2_move:
            result = "🤝 It's a tie!"
            p1_rubles = 0
            p2_rubles = 0
        else:
            winning_moves = {
                'rock': 'scissors',
                'paper': 'rock',
                'scissors': 'paper'
            }
            if winning_moves[p1_move] == p2_move:
                winner = player1
                p1_rubles = 50
                p2_rubles = -25
            else:
                winner = player2
                p1_rubles = -25
                p2_rubles = 50
        
        result_embed = discord.Embed(
            title="🎯 Game Results!",
            color=0x3498db
        )
        
        result_embed.add_field(
            name=player1['user'].display_name,
            value=move_mapping[p1_move],
            inline=True
        )
        result_embed.add_field(
            name="VS",
            value="⚔️",
            inline=True
        )
        result_embed.add_field(
            name=player2['user'].display_name,
            value=move_mapping[p2_move],
            inline=True
        )
        
        if winner:
            result_embed.add_field(
                name="Winner",
                value=f"{winner['user'].display_name} wins! 🎉",
                inline=False
            )
        else:
            result_embed.add_field(
                name="Result",
                value=result,
                inline=False
            )
        
        result_embed.add_field(
            name="Rewards/Penalties",
            value=(
                f"{player1['user'].display_name}: {p1_rubles} <a:Rubles:1344705820222292011>\n"
                f"{player2['user'].display_name}: {p2_rubles} <a:Rubles:1344705820222292011>"
            ),
            inline=False
        )
        
        await channel.send(embed=result_embed)
        
        # Update currency for both players
        for pid, amount in [(player1['user'].id, p1_rubles), (player2['user'].id, p2_rubles)]:
            user_data = get_user_data(str(channel.guild.id), str(pid))
            user_data["currency"] += amount
            save_data(server_data)
    
    except Exception as e:
        print(f"DEBUG: Game error: {e}")
        error_embed = discord.Embed(
            title="<a:Animated_Cross:1344705833627549748> Error",
            description="An error occurred in the game. Please try again.",
            color=0xff0000
        )
        try:
            await channel.send(embed=error_embed)
        except Exception as send_error:
            print(f"DEBUG: Failed to send error message: {send_error}")