import random
from discord import Embed, Color
from data_manager import get_user_data, save_data, server_data

MIN_BET = 10
MAX_BET = 2000
VALID_NUMBERS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

def calculate_multiplier(roll_type: str, roll_number: int) -> float:
    """
    Calculate win multiplier based on risk level
    High risk (near 50) = high multiplier
    Low risk (near edges) = low multiplier
    """
    if roll_type == "roll above":
        if roll_number == 90:
            return 4.0
        elif roll_number == 80:
            return 3.0
        elif roll_number == 70:
            return 2.5
        elif roll_number == 60:
            return 2.0
        elif roll_number == 50:
            return 1.5
        elif roll_number == 40:
            return 1.3
        elif roll_number == 30:
            return 1.2
        elif roll_number == 20:
            return 1.1
        elif roll_number == 10:
            return 1.05
        else:  # 100
            return 10.0  # Special case for rolling above 100 (impossible)
    else:  # roll below
        if roll_number == 10:
            return 4.0
        elif roll_number == 20:
            return 3.0
        elif roll_number == 30:
            return 2.5
        elif roll_number == 40:
            return 2.0
        elif roll_number == 50:
            return 1.5
        elif roll_number == 60:
            return 1.3
        elif roll_number == 70:
            return 1.2
        elif roll_number == 80:
            return 1.1
        elif roll_number == 90:
            return 1.05
        else:  # 100
            return 1.01  # Very safe bet

async def play_gamble(interaction, bet_amount: int, roll_type: str, roll_number: int):
    """
    Play the gambling game with predefined numbers
    """
    try:
        # Validate bet amount
        if bet_amount < MIN_BET:
            await interaction.response.send_message(
                f"❌ Minimum bet is {MIN_BET} <a:rubles:1329009278811373740>!",
                ephemeral=True
            )
            return
            
        if bet_amount > MAX_BET:
            await interaction.response.send_message(
                f"❌ Maximum bet is {MAX_BET} <a:rubles:1329009278811373740>!",
                ephemeral=True
            )
            return

        # Validate roll number
        if roll_number not in VALID_NUMBERS:
            await interaction.response.send_message(
                "❌ Invalid number! Please choose from: 10, 20, 30, 40, 50, 60, 70, 80, 90, or 100",
                ephemeral=True
            )
            return
        
        # Get user data
        user = get_user_data(interaction.guild.id, interaction.user.id)
        
        # Check if user has enough currency
        if user["currency"] < bet_amount:
            await interaction.response.send_message(
                "❌ You don't have enough currency for this bet!",
                ephemeral=True
            )
            return
        
        # Generate random number
        actual_number = random.randint(1, 100)
        
        # Get multiplier
        multiplier = calculate_multiplier(roll_type, roll_number)
        
        # Check if won
        won = (roll_type == "roll above" and actual_number > roll_number) or \
             (roll_type == "roll below" and actual_number < roll_number)
        
        # Create embed
        if won:
            winnings = int(bet_amount * multiplier)
            user["currency"] += (winnings - bet_amount)
            
            embed = Embed(
                title="🎲 WINNER! 🎲",
                color=Color.green()
            )
            embed.add_field(
                name="Roll Result",
                value=f"📊 Rolled: **{actual_number}**\n🎯 Target: **{roll_type} {roll_number}**",
                inline=False
            )
            embed.add_field(
                name="Rewards",
                value=(
                    f"✨ Multiplier: **{multiplier:.2f}x**\n"
                    f"💰 Winnings: **{winnings}** <a:rubles:1329009278811373740>"
                ),
                inline=False
            )
        else:
            user["currency"] -= bet_amount
            
            embed = Embed(
                title="💔 Better luck next time! 💔",
                color=Color.red()
            )
            embed.add_field(
                name="Roll Result",
                value=f"📊 Rolled: **{actual_number}**\n🎯 Target: **{roll_type} {roll_number}**",
                inline=False
            )
            embed.add_field(
                name="Loss",
                value=f"📉 Lost: **{bet_amount}** <a:rubles:1329009278811373740>",
                inline=False
            )
        
        # Add balance to both win/loss embeds
        embed.add_field(
            name="Balance",
            value=f"💵 New Balance: **{user['currency']}** <a:rubles:1329009278811373740>",
            inline=False
        )
        
        # Add multiplier info footer
        embed.set_footer(text=(
            f"Bet Limits: {MIN_BET}-{MAX_BET} | Valid Numbers: {', '.join(map(str, VALID_NUMBERS))} | "
            "Higher risk = Higher reward!"
        ))
        
        # Save updated user data
        save_data(server_data)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)