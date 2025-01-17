import random
from discord import Embed, Color
from data_manager import server_data, get_user_data, save_data

async def play_coinflip(interaction, bet: int, choice: str):
    try:
        user = get_user_data(interaction.guild.id, interaction.user.id)
        if user["currency"] < bet:
            await interaction.response.send_message("❌ Insufficient funds!", ephemeral=True)
            return

        # Get streak and calculate multiplier
        streak = user.get("coinflip_streak", 0)
        base_multiplier = 1.8
        streak_bonus = min(streak * 0.1, 1.0)
        multiplier = base_multiplier + streak_bonus

        # Flip coin
        result = random.choice(["heads", "tails"])
        won = choice.lower() == result

        if won:
            winnings = int(bet * multiplier)
            user["currency"] += (winnings - bet)
            user["coinflip_streak"] = streak + 1
            
            embed = Embed(title="🎲 COIN FLIP WINNER! 🎲", color=Color.green())
            embed.add_field(
                name="Result",
                value=f"💫 Flipped: **{result.upper()}**\n🎯 Your choice: **{choice.upper()}**",
                inline=False
            )
            embed.add_field(
                name="Rewards",
                value=(
                    f"🔥 Win Streak: **{user['coinflip_streak']}**\n"
                    f"✨ Multiplier: **{multiplier:.2f}x**\n"
                    f"💰 Winnings: **{winnings}** <a:rubles:1329009278811373740>"
                )
            )
        else:
            user["currency"] -= bet
            user["coinflip_streak"] = 0
            
            embed = Embed(title="💔 COIN FLIP LOSS! 💔", color=Color.red())
            embed.add_field(
                name="Result",
                value=f"💫 Flipped: **{result.upper()}**\n🎯 Your choice: **{choice.upper()}**"
            )
            embed.add_field(
                name="Loss",
                value=f"📉 Lost: **{bet}** <a:rubles:1329009278811373740>"
            )

        embed.add_field(
            name="Balance",
            value=f"💵 New Balance: **{user['currency']}** <a:rubles:1329009278811373740>"
        )
        embed.set_footer(text=f"Base: 1.8x | +0.1x per win streak (max +1.0x)")
        
        save_data(server_data)
        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

async def play_dice(interaction, bet: int, choice: str, number: int):
    try:
        user = get_user_data(interaction.guild.id, interaction.user.id)
        if user["currency"] < bet:
            await interaction.response.send_message("❌ Insufficient funds!", ephemeral=True)
            return

        # Roll dice
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2

        # Calculate result and multiplier
        won = False
        if choice == "exact":
            won = total == number
            multiplier = 5.0
        elif choice == "over":
            won = total > number
            multiplier = 12 / (12 - number)
        else:  # under
            won = total < number
            multiplier = 12 / (number - 1)

        if won:
            winnings = int(bet * multiplier)
            user["currency"] += (winnings - bet)
            
            embed = Embed(title="🎲 DICE ROLL WINNER! 🎲", color=Color.green())
            embed.add_field(
                name="Roll Result",
                value=f"🎲 Dice: **{dice1}** + **{dice2}** = **{total}**\n🎯 Your bet: **{choice} {number}**"
            )
            embed.add_field(
                name="Rewards",
                value=(
                    f"✨ Multiplier: **{multiplier:.2f}x**\n"
                    f"💰 Winnings: **{winnings}** <a:rubles:1329009278811373740>"
                )
            )
        else:
            user["currency"] -= bet
            
            embed = Embed(title="💔 DICE ROLL LOSS! 💔", color=Color.red())
            embed.add_field(
                name="Roll Result",
                value=f"🎲 Dice: **{dice1}** + **{dice2}** = **{total}**\n🎯 Your bet: **{choice} {number}**"
            )
            embed.add_field(
                name="Loss",
                value=f"📉 Lost: **{bet}** <a:rubles:1329009278811373740>"
            )

        embed.add_field(
            name="Balance",
            value=f"💵 New Balance: **{user['currency']}** <a:rubles:1329009278811373740>"
        )
        embed.set_footer(text="Exact: 5x | Over/Under: Multiplier varies by number")
        
        save_data(server_data)
        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

async def play_colorwheel(interaction, bet: int, color: str):
    try:
        user = get_user_data(interaction.guild.id, interaction.user.id)
        if user["currency"] < bet:
            await interaction.response.send_message("❌ Insufficient funds!", ephemeral=True)
            return

        # Spin wheel
        result = random.choices(
            ["green", "red", "black"],
            weights=[1, 6.5, 6.5]
        )[0]

        multipliers = {
            "green": 14.0,
            "red": 2.0,
            "black": 2.0
        }

        won = color.lower() == result
        multiplier = multipliers[color.lower()]

        if won:
            winnings = int(bet * multiplier)
            user["currency"] += (winnings - bet)
            
            embed = Embed(title="🎡 COLOR WHEEL WINNER! 🎡", color=Color.green())
            embed.add_field(
                name="Spin Result",
                value=f"🎨 Landed on: **{result.upper()}**\n🎯 Your choice: **{color.upper()}**"
            )
            embed.add_field(
                name="Rewards",
                value=(
                    f"✨ Multiplier: **{multiplier:.2f}x**\n"
                    f"💰 Winnings: **{winnings}** <a:rubles:1329009278811373740>"
                )
            )
        else:
            user["currency"] -= bet
            
            embed = Embed(title="💔 COLOR WHEEL LOSS! 💔", color=Color.red())
            embed.add_field(
                name="Spin Result",
                value=f"🎨 Landed on: **{result.upper()}**\n🎯 Your choice: **{color.upper()}**"
            )
            embed.add_field(
                name="Loss",
                value=f"📉 Lost: **{bet}** <a:rubles:1329009278811373740>"
            )

        embed.add_field(
            name="Balance",
            value=f"💵 New Balance: **{user['currency']}** <a:rubles:1329009278811373740>"
        )
        embed.set_footer(text="Green: 14x | Red: 2x | Black: 2x")
        
        save_data(server_data)
        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)