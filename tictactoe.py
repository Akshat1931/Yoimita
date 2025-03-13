import discord
from discord import Embed, Color
from discord.ext import commands
from typing import List, Dict
from data_manager import get_user_rubles, update_rubles

MIN_BET = 100
MAX_BET = 1000

# Track active games
active_games: Dict[int, bool] = {}

class TicTacToeView(discord.ui.View):
    def __init__(self, challenger: discord.Member, opponent: discord.Member, bet_amount: int):
        super().__init__(timeout=300)  # Add 5 minute timeout
        self.challenger = challenger
        self.opponent = opponent
        self.current_player = challenger
        self.bet_amount = bet_amount
        self.board = [[" " for _ in range(3)] for _ in range(3)]
        self.game_over = False
        
        # Add buttons
        for y in range(3):
            for x in range(3):
                # Convert position to string for unique button custom_id
                button_pos = f"{x}-{y}"
                self.add_item(TicTacToeButton(x, y, button_pos))

    async def on_timeout(self):
        """Handle game timeout"""
        if not self.game_over:
            # Return bets to both players
            update_rubles(str(self.challenger.guild.id), str(self.challenger.id), self.bet_amount)
            update_rubles(str(self.challenger.guild.id), str(self.opponent.id), self.bet_amount)
            
            # Disable all buttons
            for child in self.children:
                child.disabled = True
                
            # Remove from active games
            active_games.pop(self.challenger.id, None)
            active_games.pop(self.opponent.id, None)
            
            # Update message
            embed = Embed(
                title="🎮 Game Over!",
                description="⏰ Game timed out! Bets have been returned.",
                color=Color.red()
            )
            
            try:
                await self.message.edit(view=self, embed=embed)
            except:
                pass

    def check_winner(self) -> bool:
        # Check rows
        for row in self.board:
            if row.count(row[0]) == 3 and row[0] != " ":
                return True

        # Check columns
        for col in range(3):
            if self.board[0][col] == self.board[1][col] == self.board[2][col] != " ":
                return True

        # Check diagonals
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != " ":
            return True
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != " ":
            return True

        return False

    def is_board_full(self) -> bool:
        return all(cell != " " for row in self.board for cell in row)

class TicTacToeButton(discord.ui.Button):
    def __init__(self, x: int, y: int, custom_id: str):
        # Initialize with required custom_id and proper label
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="\u200b",  # Zero-width space as label
            custom_id=f"ttt_{custom_id}",
            row=y
        )
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view: TicTacToeView = self.view

        # Store message reference for timeout handling
        view.message = interaction.message

        if interaction.user not in [view.challenger, view.opponent]:
            await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> This is not your game!", ephemeral=True)
            return

        if interaction.user != view.current_player:
            await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> It's not your turn!", ephemeral=True)
            return

        if view.game_over:
            await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> This game is already over!", ephemeral=True)
            return

        if view.board[self.y][self.x] != " ":
            await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> This space is already taken!", ephemeral=True)
            return

        # Update board and button
        symbol = "X" if view.current_player == view.challenger else "O"
        view.board[self.y][self.x] = symbol
        self.style = discord.ButtonStyle.danger if view.current_player == view.challenger else discord.ButtonStyle.success
        self.label = symbol
        self.disabled = True

        # Check for winner
        if view.check_winner():
            view.game_over = True
            for child in view.children:
                child.disabled = True
            
            # Award winner and deduct from loser
            winner_id = str(view.current_player.id)
            loser = view.opponent if view.current_player == view.challenger else view.challenger
            loser_id = str(loser.id)
            
            winnings = view.bet_amount * 2
            update_rubles(str(interaction.guild_id), winner_id, winnings)
            
            embed = Embed(
                title="🎮 Game Over!",
                description=f"🏆 {view.current_player.mention} wins {winnings} <a:Rubles:1344705820222292011>!",
                color=Color.green()
            )
            
            # Remove from active games
            active_games.pop(view.challenger.id, None)
            active_games.pop(view.opponent.id, None)
            
            await interaction.response.edit_message(view=view, embed=embed)
            return

        # Check for draw
        if view.is_board_full():
            view.game_over = True
            for child in view.children:
                child.disabled = True
                
            # Return bets to both players
            update_rubles(str(interaction.guild_id), str(view.challenger.id), view.bet_amount)
            update_rubles(str(interaction.guild_id), str(view.opponent.id), view.bet_amount)
            
            embed = Embed(
                title="🎮 Game Over!",
                description="🤝 It's a draw! Bets have been returned.",
                color=Color.blue()
            )
            
            # Remove from active games
            active_games.pop(view.challenger.id, None)
            active_games.pop(view.opponent.id, None)
            
            await interaction.response.edit_message(view=view, embed=embed)
            return

        # Switch turns
        view.current_player = view.opponent if view.current_player == view.challenger else view.challenger
        
        embed = Embed(
            title="🎮 Tic Tac Toe",
            description=f"It's {view.current_player.mention}'s turn!",
            color=Color.blue()
        )
        
        await interaction.response.edit_message(view=view, embed=embed)

async def tictactoe_bet(interaction: discord.Interaction, opponent: discord.Member, bet_amount: int):
    """Start a betting Tic Tac Toe game"""
    
    # Check if either player is in an active game
    if interaction.user.id in active_games or opponent.id in active_games:
        await interaction.response.send_message("<a:Animated_Cross:1344705833627549748> One of the players is already in a game!", ephemeral=True)
        return

    # Validate bet amount
    if bet_amount < MIN_BET or bet_amount > MAX_BET:
        await interaction.response.send_message(
            f"<a:Animated_Cross:1344705833627549748> Bet amount must be between {MIN_BET} and {MAX_BET} <a:Rubles:1344705820222292011>!",
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
    
    embed = Embed(
        title="🎮 Tic Tac Toe",
        description=f"Game started between {interaction.user.mention} and {opponent.mention}\n"
                   f"Bet amount: {bet_amount} <a:Rubles:1344705820222292011>\n\n"
                   f"It's {interaction.user.mention}'s turn!",
        color=Color.blue()
    )
    
    await interaction.response.send_message(
        content=f"{interaction.user.mention} vs {opponent.mention}",
        embed=embed,
        view=view
    )