from pkgutil import get_data
import random
from discord import Embed, Color, Interaction
import discord
from discord.ui import Button, View
import datetime
from data_manager import get_user_data, save_data, server_data
import asyncio

MIN_BET = 10
MAX_BET = 2000

class Card:
    def __init__(self, suit, value):
        self.suit = suit
        self.value = value
    
    def __str__(self):
        return f"{self.value}{self.suit}"
    
    def get_value(self):
        if self.value in ['J', 'Q', 'K']:
            return 10
        elif self.value == 'A':
            return 11
        return int(self.value)

class BlackjackGame:
    def __init__(self):
        self.suits = ['♠️', '♥️', '♣️', '♦️']
        self.values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        self.deck = [Card(suit, value) for suit in self.suits for value in self.values]
        random.shuffle(self.deck)
        
    def deal_card(self):
        return self.deck.pop()
    
    def calculate_hand(self, hand):
        value = 0
        aces = 0
        
        for card in hand:
            if card.value == 'A':
                aces += 1
            else:
                value += card.get_value()
        
        # Add aces
        for _ in range(aces):
            if value + 11 <= 21:
                value += 11
            else:
                value += 1
                
        return value

class BlackjackView(View):
    def __init__(self, game, player_hand, dealer_hand, bet_amount, user):
        super().__init__(timeout=30)
        self.game = game
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.bet_amount = bet_amount
        self.user = user
        self.ended = False
        
    @property
    def player_value(self):
        return self.game.calculate_hand(self.player_hand)
    
    @property
    def dealer_value(self):
        return self.game.calculate_hand(self.dealer_hand)
    
    def create_embed(self, show_dealer=False):
        embed = Embed(
            title="🎰 Blackjack",
            color=Color.gold(),
            timestamp=datetime.datetime.utcnow()
        )
        
        # Show dealer's hand (first card hidden unless show_dealer is True)
        dealer_cards = f"{self.dealer_hand[0] if show_dealer else '🎴'} "
        dealer_cards += " ".join(str(card) for card in self.dealer_hand[1:])
        dealer_value = self.dealer_value if show_dealer else "?"
        embed.add_field(
            name="Dealer's Hand",
            value=f"{dealer_cards}\nValue: {dealer_value}",
            inline=False
        )
        
        # Show player's hand
        player_cards = " ".join(str(card) for card in self.player_hand)
        embed.add_field(
            name="Your Hand",
            value=f"{player_cards}\nValue: {self.player_value}",
            inline=False
        )
        
        embed.add_field(
            name="Bet Amount",
            value=f"{self.bet_amount:,} <a:Rubles:1344705820222292011>",
            inline=False
        )
        
        return embed
    
    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.user.id:
            return
            
        self.player_hand.append(self.game.deal_card())
        
        if self.player_value > 21:
            self.ended = True
            for item in self.children:
                item.disabled = True
            
            embed = self.create_embed(show_dealer=True)
            embed.description = "<a:Animated_Cross:1344705833627549748> Bust! You went over 21!"
            await interaction.response.edit_message(embed=embed, view=self)
            return
            
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
    
    @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary)
    async def stand(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.user.id:
            return
            
        self.ended = True
        
        # Dealer draws until 17 or higher
        while self.dealer_value < 17:
            self.dealer_hand.append(self.game.deal_card())
        
        for item in self.children:
            item.disabled = True
            
        embed = self.create_embed(show_dealer=True)
        
        # Determine winner
        if self.dealer_value > 21:
            embed.description = "🎉 Dealer bust! You win!"
            winnings = self.bet_amount * 1.8  # Lowered multiplier
        elif self.dealer_value < self.player_value:
            embed.description = "🎉 You win!"
            winnings = self.bet_amount * 1.8  # Lowered multiplier
        elif self.dealer_value > self.player_value:
            embed.description = "<a:Animated_Cross:1344705833627549748> Dealer wins!"
            winnings = 0
        else:
            embed.description = "🤝 Push! Bet returned."
            winnings = self.bet_amount
            
        # Update user's currency
        user_data = get_user_data(interaction.guild.id, self.user.id)
        user_data["currency"] += winnings
        save_data(server_data)
        
        embed.add_field(
            name="Results",
            value=f"Winnings: {winnings:,} <a:Rubles:1344705820222292011>\n"
                  f"New Balance: {user_data['currency']:,} <a:Rubles:1344705820222292011>",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=self)

async def play_blackjack(interaction: Interaction, bet_amount: int):
    """
    Start a new game of blackjack
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
        
        # Get user data and check balance
        user_data = get_user_data(interaction.guild.id, interaction.user.id)
        if user_data["currency"] < bet_amount:
            await interaction.response.send_message(
                "<a:Animated_Cross:1344705833627549748> You don't have enough rubles for this bet!",
                ephemeral=True
            )
            return
            
        # Deduct bet amount
        user_data["currency"] -= bet_amount
        save_data(server_data)
        
        # Initialize game
        game = BlackjackGame()
        player_hand = [game.deal_card(), game.deal_card()]
        dealer_hand = [game.deal_card(), game.deal_card()]
        
        # Create view with buttons
        view = BlackjackView(game, player_hand, dealer_hand, bet_amount, interaction.user)
        
        # Check for natural blackjack
        if game.calculate_hand(player_hand) == 21:
            view.ended = True
            for item in view.children:
                item.disabled = True
            embed = view.create_embed(show_dealer=True)
            
            if game.calculate_hand(dealer_hand) == 21:
                embed.description = "🤝 Both have Blackjack! Push!"
                winnings = bet_amount
            else:
                embed.description = "🎉 Blackjack! You win!"
                winnings = int(bet_amount * 2.2)  # Lowered multiplier
                
            user_data["currency"] += winnings
            save_data(server_data)
            
            embed.add_field(
                name="Results",
                value=f"Winnings: {winnings:,} <a:Rubles:1344705820222292011>\n"
                      f"New Balance: {user_data['currency']:,} <a:Rubles:1344705820222292011>",
                inline=False
            )
        else:
            embed = view.create_embed()
            
        await interaction.response.send_message(embed=embed, view=view)
        
    except Exception as e:
        # Refund bet if error occurs
        if 'user_data' in locals() and 'bet_amount' in locals():
            user_data["currency"] += bet_amount
            save_data(server_data)
            
        await interaction.response.send_message(
            f"<a:Animated_Cross:1344705833627549748> An error occurred: {str(e)}", 
            ephemeral=True
        )


#--------------------------------------------------#------------------------------------------------------

MIN_BET = 10
MAX_BET = 1000

# Plinko board configurations for different risk levels
PLINKO_CONFIGS = {
    "low": {
        "multipliers": [1.2, 1.0, 0.8, 0.8, 1.0, 1.2],
        "color": Color.green(),
        "name": "Low Risk"
    },
    "medium": {
        "multipliers": [2.0, 1.1, 0.0, 0.6, 1.1, 2.0],
        "color": Color.blue(),
        "name": "Medium Risk"
    },
    "high": {
        "multipliers": [3.0, 1.3, 0.0, 0.0, 1.3, 3.0],  # Added 0.0 multipliers for high risk
        "color": Color.red(),
        "name": "High Risk"
    }
}

class PlinkoGame:
    def __init__(self, risk_level, rows=8):
        self.risk_level = risk_level
        self.rows = rows
        self.multipliers = PLINKO_CONFIGS[risk_level]["multipliers"]
        self.path = []
        self.current_position = len(self.multipliers) // 2  # Start in middle
        
    def simulate_drop(self):
        self.path = []
        position = self.current_position
        
        for _ in range(self.rows):
            # Add current position to path
            self.path.append(position)
            
            # Calculate probabilities based on risk level and position
            go_left = random.random() < 0.5
            
            # Move ball
            if go_left and position > 0:
                position -= 1
            elif not go_left and position < len(self.multipliers) - 1:
                position += 1
                
        self.path.append(position)  # Final position
        return self.multipliers[position]

class PlinkoView(View):
    def __init__(self, game, bet_amount, user):
        super().__init__(timeout=30)
        self.game = game
        self.bet_amount = bet_amount
        self.user = user
        self.message = None
        
    def create_board_display(self, current_row=-1):
        """Create visual representation of the Plinko board"""
        board = []
        multipliers = self.game.multipliers
        path = self.game.path
        
        # Add multiplier row at bottom
        mult_row = ""
        for m in multipliers:
            mult_row += f"{m}x ".rjust(4)
        board.append(mult_row)
        
        # Create the board with pegs
        for row in range(self.game.rows):
            line = ""
            for col in range(len(multipliers)):
                if row == current_row and col == path[row]:
                    line += "🔴 "  # Ball
                else:
                    line += "⚫ "  # Peg
            board.append(line)
            
        # Reverse board (except multipliers) for proper display
        board[1:] = board[1:][::-1]
        
        return "```\n" + "\n".join(board) + "\n```"

    def create_embed(self, current_row=-1, final_multiplier=None):
        config = PLINKO_CONFIGS[self.game.risk_level]
        embed = Embed(
            title="🎯 Plinko",
            description=f"Risk Level: {config['name']}\n"
                       f"Bet Amount: {self.bet_amount:,} <a:Rubles:1344705820222292011>",
            color=config["color"]
        )
        
        embed.add_field(
            name="Board",
            value=self.create_board_display(current_row),
            inline=False
        )
        
        if final_multiplier is not None:
            winnings = int(self.bet_amount * final_multiplier)
            embed.add_field(
                name="Results",
                value=f"Multiplier: {final_multiplier}x\n"
                      f"Winnings: {winnings:,} <a:Rubles:1344705820222292011>\n"
                      f"New Balance: {get_user_data(self.user.guild.id, self.user.id)['currency']:,} <a:Rubles:1344705820222292011>",
                inline=False
            )
            
        return embed

    @discord.ui.button(label="Drop Ball", style=discord.ButtonStyle.primary)
    async def drop(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.user.id:
            return
            
        # Disable button
        button.disabled = True
        await interaction.response.edit_message(view=self)
        
        # Simulate the drop
        final_multiplier = self.game.simulate_drop()
        
        # Animate the drop
        for row in range(self.game.rows + 1):
            embed = self.create_embed(row)
            await self.message.edit(embed=embed)
            await asyncio.sleep(0.5)
            
        # Show final result
        embed = self.create_embed(final_multiplier=final_multiplier)
        
        # Update user's currency
        winnings = int(self.bet_amount * final_multiplier)
        user_data = get_user_data(interaction.guild_id, self.user.id)
        user_data["currency"] += winnings
        save_data(server_data)
        
        await self.message.edit(embed=embed, view=self)

async def play_plinko(interaction: Interaction, bet_amount: int, risk_level: str = "medium"):
    """Start a new game of Plinko"""
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
            
        # Validate risk level
        if risk_level not in PLINKO_CONFIGS:
            await interaction.response.send_message(
                "<a:Animated_Cross:1344705833627549748> Invalid risk level! Choose 'low', 'medium', or 'high'.",
                ephemeral=True
            )
            return
            
        # Check user's balance
        user_data = get_user_data(interaction.guild_id, interaction.user.id)
        if user_data["currency"] < bet_amount:
            await interaction.response.send_message(
                "<a:Animated_Cross:1344705833627549748> You don't have enough rubles for this bet!",
                ephemeral=True
            )
            return
            
        # Deduct bet amount
        user_data["currency"] -= bet_amount
        save_data(server_data)
        
        # Initialize game
        game = PlinkoGame(risk_level)
        view = PlinkoView(game, bet_amount, interaction.user)
        
        # Send initial board
        await interaction.response.send_message(
            embed=view.create_embed(),
            view=view
        )
        view.message = await interaction.original_response()
        
    except Exception as e:
        # Refund bet if error occurs
        if 'user_data' in locals() and 'bet_amount' in locals():
            user_data["currency"] += bet_amount
            save_data(server_data)
            
        await interaction.response.send_message(
            f"<a:Animated_Cross:1344705833627549748> An error occurred: {str(e)}",
            ephemeral=True
        )