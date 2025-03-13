import discord
import asyncio
import random
import operator
from data_manager import get_user_data, save_data, server_data

class MathQuizView(discord.ui.View):
    def __init__(self, correct_answer, timeout):
        super().__init__(timeout=timeout)
        self.correct_answer = correct_answer
        self.players = {}
        self.done_event = asyncio.Event()
        self.timed_out = False
        
        # Generate answer options
        options = self.generate_options(correct_answer)
        
        # Create the select menu with random options
        select = discord.ui.Select(
            placeholder="Choose your answer!",
            options=[discord.SelectOption(label=str(opt), value=str(opt)) for opt in options]
        )
        select.callback = self.select_callback
        self.add_item(select)

    def generate_options(self, correct_answer):
        """Generate 9 wrong options and include the correct answer."""
        options = {correct_answer}
        
        # Generate wrong options around the correct answer
        while len(options) < 10:
            # Generate numbers within a reasonable range of the correct answer
            wrong_answer = correct_answer + random.randint(-20, 20)
            if wrong_answer != correct_answer:
                options.add(wrong_answer)
                
        # Convert to list and shuffle
        options = list(options)
        random.shuffle(options)
        return options

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id in self.players:
            await interaction.response.send_message("You've already answered!", ephemeral=True)
            return
        
        selected_answer = int(interaction.data['values'][0])
        is_correct = selected_answer == self.correct_answer
        
        self.players[interaction.user.id] = {
            'user': interaction.user,
            'answer': selected_answer,
            'is_correct': is_correct
        }
        
        await interaction.response.send_message(
            f"You chose {selected_answer}!" + (" <a:animated_tick:1336385852804431873>" if is_correct else " <a:Animated_Cross:1344705833627549748>"),
            ephemeral=True
        )
        
        if is_correct:
            self.done_event.set()
            self.stop()

    async def on_timeout(self):
        self.timed_out = True
        self.done_event.set()
        await super().on_timeout()

async def play_mathquiz(channel):
    """A math quiz game where players solve a random math problem."""
    try:
        # Random taunt messages for losers
        taunt_messages = [
            "Get off from discord and study! 📚",
            "Time to dust off that math textbook! 📖",
            "Studies first, Discord later! 📱❌",
            "Your math teacher would be disappointed... 😢",
            "Quick! Hide this result from your parents! 🙈",
            "Have you considered getting a tutor? 🤓",
            "Your grades have left the chat... 💨",
            "Error 404: Study habits not found 🔍",
            "Study streak: 0 days. Discord streak: ∞ days 📈",
            "Your books are gathering more dust than XP right now 🎮😅",
            "Pixels temporary, knowledge forever! 🧠✨",
        ]
        
        # Generate random math problem
        operations = [
            (operator.add, "+"),
            (operator.sub, "-"),
            (operator.mul, "×")
        ]
        op_func, op_symbol = random.choice(operations)
        
        # Generate numbers based on operation
        if op_func == operator.mul:
            num1 = random.randint(2, 12)
            num2 = random.randint(2, 12)
        else:
            num1 = random.randint(1, 100)
            num2 = random.randint(1, 100)
        
        correct_answer = op_func(num1, num2)
        
        # Create question embed
        question_embed = discord.Embed(
            title="🧮 Math Quiz Time!",
            description=(
                f"What is **{num1} {op_symbol} {num2}**?\n\n"
                "Choose your answer from the dropdown menu!\n"
                "You have 20 seconds to answer!"
            ),
            color=0x3498db  # Blue color
        )
        question_embed.set_footer(text="First person to get it right wins!")
        
        view = MathQuizView(correct_answer, timeout=20)
        message = await channel.send(embed=question_embed, view=view)
        
        await view.done_event.wait()
        await message.edit(view=None)  # Remove the dropdown
        
        # Create result embed
        result_embed = discord.Embed(
            title="📊 Quiz Results",
            color=0x2ecc71 if any(p['is_correct'] for p in view.players.values()) else 0xe74c3c
        )
        
        result_embed.add_field(
            name="Problem",
            value=f"{num1} {op_symbol} {num2} = **{correct_answer}**",
            inline=False
        )
        
        # Handle winners and participants
        winners = [p for p in view.players.values() if p['is_correct']]
        losers = [p for p in view.players.values() if not p['is_correct']]
        
        if winners:
            winner = winners[0]
            result_embed.add_field(
                name="🏆 Winner",
                value=(
                    f"{winner['user'].mention} got it right!\n"
                    f"Prize: +50 <a:Rubles:1344705820222292011>"
                ),
                inline=False
            )
            
            # Award currency to winner
            user_data = get_user_data(str(channel.guild.id), str(winner['user'].id))
            user_data["currency"] += 50
            save_data(server_data)
            
            # Handle losers and deduct their currency
            if losers:
                loser_mentions = []
                for loser in losers:
                    user_data = get_user_data(str(channel.guild.id), str(loser['user'].id))
                    user_data["currency"] -= 50
                    save_data(server_data)
                    loser_mentions.append(f"{loser['user'].mention}: -50 <a:Rubles:1344705820222292011>")
                
                result_embed.add_field(
                    name="😢 Better Luck Next Time!",
                    value="\n".join(loser_mentions) + f"\n\n{random.choice(taunt_messages)}",
                    inline=False
                )
        else:
            result_embed.add_field(
                name="<a:Animated_Cross:1344705833627549748> No Winners",
                value="Nobody got the correct answer!\n\n" + random.choice(taunt_messages),
                inline=False
            )
        
        # Show all participants and their answers
        if view.players:
            participants = "\n".join(
                f"{p['user'].mention}: {p['answer']}" for p in view.players.values()
            )
            result_embed.add_field(
                name="👥 Participants",
                value=participants,
                inline=False
            )
        else:
            result_embed.add_field(
                name="😢 No Participants",
                value="Nobody tried to answer",
                inline=False
            )
        
        await channel.send(embed=result_embed)
    
    except Exception as e:
        error_embed = discord.Embed(
            title="<a:Animated_Cross:1344705833627549748> Game Error",
            description="The quiz failed to complete properly",
            color=0xFF0000
        )
        await channel.send(embed=error_embed)
        print(f"Quiz error: {e}")