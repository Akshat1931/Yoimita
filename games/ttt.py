import discord
from discord.ui import Button, View
from datetime import datetime, timedelta
import random
import asyncio
from data_manager import server_data, get_user_data, save_data

class TicTacToeButton(Button):
    def __init__(self, x, y):
        super().__init__(
            style=discord.ButtonStyle.secondary, 
            label="⠀",
            custom_id=f"{x}-{y}",
            row=x
        )
        self.x = x
        self.y = y

class TicTacToeGame(View):
    def __init__(self, player1, player2):
        super().__init__(timeout=300)
        self.player1 = player1
        self.player2 = player2
        self.current_player = player1
        self.board = [[None for _ in range(3)] for _ in range(3)]
        self.winner = None
        self.game_over = False
        self.countdown_time = 15  # 15 seconds for each turn
        self.countdown_task = None
        
        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y))
    
    def check_winner(self):
        # Check rows
        for row in self.board:
            if row.count(row[0]) == 3 and row[0] is not None:
                return row[0]
        
        # Check columns
        for col in range(3):
            if (self.board[0][col] == self.board[1][col] == self.board[2][col] 
                and self.board[0][col] is not None):
                return self.board[0][col]
        
        # Check diagonals
        if (self.board[0][0] == self.board[1][1] == self.board[2][2] 
            and self.board[0][0] is not None):
            return self.board[0][0]
        if (self.board[0][2] == self.board[1][1] == self.board[2][0] 
            and self.board[0][2] is not None):
            return self.board[0][2]
        
        # Check for tie
        if all(all(cell is not None for cell in row) for row in self.board):
            return "tie"
        
        return None

    async def start_countdown(self):
        try:
            while self.countdown_time > 0 and not self.game_over:
                turn_embed = discord.Embed(
                    title="🎮 Tic Tac Toe",
                    description=f"It's {self.current_player.mention}'s turn!\nTime remaining: {self.countdown_time}s",
                    color=0x3498db
                )
                await self.message.edit(embed=turn_embed)
                await asyncio.sleep(1)
                self.countdown_time -= 1
                
            if not self.game_over and self.countdown_time <= 0:
                self.game_over = True
                for item in self.children:
                    item.disabled = True
                
                # Get the player who didn't make their move (current_player)
                losing_player = self.current_player
                winning_player = self.player2 if losing_player == self.player1 else self.player1
                loser_data = get_user_data(str(self.message.guild.id), str(losing_player.id))
                winner_data = get_user_data(str(self.message.guild.id), str(winning_player.id))
                
                loser_data["currency"] -= 100
                winner_data["currency"] += 100
                
                save_data(server_data)
                
                timeout_embed = discord.Embed(
                    title="⏰ Game Over - Time's Up!",
                    description=f"{losing_player.mention} took too long to make a move!\n\n"
                              f"{winning_player.mention} wins 100 <a:Rubles:1344705820222292011>\n"
                              f"{losing_player.mention} loses 100 <a:Rubles:1344705820222292011>",
                    color=0xe74c3c
                )
                await self.message.edit(embed=timeout_embed, view=self)
        except Exception as e:
            print(f"Error in countdown: {e}")

    async def handle_click(self, button: TicTacToeButton, interaction: discord.Interaction):
        if self.game_over:
            await interaction.response.send_message("The game is already over!", ephemeral=True)
            return
        
        if interaction.user.id != self.current_player.id:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
        
        x, y = button.x, button.y
        
        if self.board[x][y] is not None:
            await interaction.response.send_message("That space is already taken!", ephemeral=True)
            return
        
        # Reset countdown for next turn
        self.countdown_time = 15
        
        # Update the board
        is_x_player = self.current_player == self.player1
        self.board[x][y] = "X" if is_x_player else "O"
        button.label = "❌" if is_x_player else "⭕"
        button.style = discord.ButtonStyle.danger if is_x_player else discord.ButtonStyle.success
        button.disabled = True
        
        # Check for winner
        winner = self.check_winner()
        if winner:
            self.game_over = True
            for item in self.children:
                item.disabled = True
            
            if winner == "tie":
                game_embed = discord.Embed(
                    title="🤝 Game Over - It's a Tie!",
                    description="Nobody wins this time!",
                    color=0x95a5a6
                )
            else:
                winning_player = self.player1 if winner == "X" else self.player2
                losing_player = self.player2 if winner == "X" else self.player1
                
                # Update currencies using data_manager
                winner_data = get_user_data(str(interaction.guild.id), str(winning_player.id))
                loser_data = get_user_data(str(interaction.guild.id), str(losing_player.id))
                
                winner_data["currency"] += 100
                loser_data["currency"] -= 100
                
                save_data(server_data)
                
                game_embed = discord.Embed(
                    title="🎉 Game Over - Winner!",
                    description=f"{winning_player.mention} wins the game!",
                    color=0x2ecc71
                )
                game_embed.add_field(
                    name="Rewards",
                    value=f"{winning_player.mention} wins 100 <a:Rubles:1344705820222292011>\n"
                          f"{losing_player.mention} loses 100 <a:Rubles:1344705820222292011>",
                    inline=False
                )
            
            await interaction.response.edit_message(content=None, embed=game_embed, view=self)
            return
        
        # Switch players
        self.current_player = self.player2 if is_x_player else self.player1
        
        # Update turn embed
        turn_embed = discord.Embed(
            title="🎮 Tic Tac Toe",
            description=f"It's {self.current_player.mention}'s turn!\nTime remaining: {self.countdown_time}s",
            color=0x3498db
        )
        
        await interaction.response.edit_message(embed=turn_embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.data.get("custom_id"):
            x, y = map(int, interaction.data["custom_id"].split("-"))
            await self.handle_click(self.children[x * 3 + y], interaction)
        return True
    
    async def on_timeout(self):
        if not self.game_over:
            for child in self.children:
                child.disabled = True
            timeout_embed = discord.Embed(
                title="⏰ Game Over - Timeout",
                description="Game timed out due to inactivity!",
                color=0xe74c3c
            )
            try:
                await self.message.edit(embed=timeout_embed, view=self)
            except:
                pass

async def start_tictactoe(channel):
    """Start a game of Tic Tac Toe."""
    try:
        # Get all unique authors from recent messages
        unique_authors = set()
        async for message in channel.history(limit=50):
            if not message.author.bot:  # Exclude bots
                unique_authors.add(message.author)
        
        # Convert to list and shuffle
        players = list(unique_authors)
        if len(players) < 2:
            error_embed = discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Error",
                description="Not enough players! Need at least 2 people who have sent messages recently.",
                color=0xe74c3c
            )
            await channel.send(embed=error_embed)
            return
            
        # Select 2 random players
        random.shuffle(players)
        player1, player2 = random.sample(players, 2)
        
        # Ping the selected players
        await channel.send(f"{player1.mention} and {player2.mention}, you have been selected to play Tic Tac Toe!")
        
        # Create start game embed
        start_embed = discord.Embed(
            title="🎮 Tic Tac Toe",
            description=f"{player1.mention} (❌) vs {player2.mention} (⭕)\n\n"
                       f"It's {player1.mention}'s turn!\nTime remaining: 15s",
            color=0x3498db
        )
        
        # Create and start game
        game = TicTacToeGame(player1, player2)
        msg = await channel.send(embed=start_embed, view=game)
        game.message = msg
        
        # Start the countdown
        asyncio.create_task(game.start_countdown())
        
    except Exception as e:
        print(f"DEBUG: Error in Tic Tac Toe: {e}")
        error_embed = discord.Embed(
            title="<a:Animated_Cross:1344705833627549748> Error",
            description="An error occurred while starting the game.",
            color=0xe74c3c
        )
        await channel.send(embed=error_embed)