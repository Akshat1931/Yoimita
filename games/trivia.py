import random
import asyncio
import discord
from data_manager import server_data, get_user_data, save_data

# Sample trivia questions
TRIVIA_QUESTIONS = [
    {
        "question": "What is the largest planet in our solar system?",
        "answer": ["jupiter"],
        "fact": "Jupiter is so large that all other planets in our solar system could fit inside it!"
    },
    {
        "question": "Which element has the chemical symbol 'Au'?",
        "answer": ["gold"],
        "fact": "The symbol Au comes from the Latin word for gold, 'aurum'."
    },
    {
        "question": "What is the capital city of Japan?",
        "answer": ["tokyo"],
        "fact": "Tokyo is the world's most populous metropolitan area!"
    }
]

async def play_trivia(channel):
    """A trivia game with free-form answers."""
    try:
        # Select random question
        question_data = random.choice(TRIVIA_QUESTIONS)
        correct_answers = [ans.lower() for ans in question_data["answer"]]
        
        # Create question embed
        question_embed = discord.Embed(
            title="🎯 Trivia Time!",
            description=question_data["question"],
            color=0x9b59b6  # Purple color
        )
        question_embed.set_footer(text="You have 30 seconds to answer! Just type your answer in the chat.")
        
        await channel.send(embed=question_embed)

        # Get bot instance
        bot = channel.guild.me._state._get_client()
        
        # Keep track of who has answered
        answered_users = set()
        
        def check(msg):
            return (
                msg.channel.id == channel.id and
                not msg.author.bot and
                len(msg.content) > 0
            )

        end_time = asyncio.get_event_loop().time() + 30
        while asyncio.get_event_loop().time() < end_time:
            try:
                remaining_time = max(0.1, end_time - asyncio.get_event_loop().time())
                msg = await bot.wait_for('message', check=check, timeout=remaining_time)
                
                # Process the answer
                user = msg.author
                user_answer = msg.content.lower().strip()
                
                # Prevent multiple answers from same user
                if user.id in answered_users:
                    continue
                
                answered_users.add(user.id)
                
                if user_answer in correct_answers:
                    # Correct answer embed
                    winner_embed = discord.Embed(
                        title="✨ Correct Answer!",
                        description=f"Well done {user.mention}!\nYou got it right!",
                        color=0x2ecc71  # Green color
                    )
                    winner_embed.add_field(
                        name="Fun Fact",
                        value=question_data["fact"],
                        inline=False
                    )
                    winner_embed.add_field(
                        name="Prize",
                        value="You win 150 <a:rubles:1329009278811373740>!",
                        inline=False
                    )
                    await channel.send(embed=winner_embed)
                    
                    # Award currency
                    user_data = get_user_data(str(channel.guild.id), str(user.id))
                    user_data["currency"] += 150
                    save_data(server_data)
                    return
                else:
                    # Wrong answer embed
                    wrong_embed = discord.Embed(
                        title="❌ Wrong Answer!",
                        description=f"Sorry {user.mention}, that's not correct!",
                        color=0xe74c3c  # Red color
                    )
                    wrong_embed.set_footer(text="Someone else can still try!")
                    await channel.send(embed=wrong_embed)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"DEBUG: Error processing answer: {e}")
                continue
        
        # Time's up embed
        timeout_embed = discord.Embed(
            title="⌛ Time's up!",
            description=f"The correct answer was **{correct_answers[0].title()}**!",
            color=0x95a5a6  # Gray color
        )
        
        timeout_embed.add_field(
            name="Fun Fact",
            value=question_data["fact"],
            inline=False
        )
        
        if answered_users:
            players = ", ".join([f"<@{uid}>" for uid in answered_users])
            timeout_embed.add_field(
                name="Thanks for playing!",
                value=players,
                inline=False
            )
        else:
            timeout_embed.add_field(
                name="Participants",
                value="Nobody tried to answer 😢",
                inline=False
            )
            
        await channel.send(embed=timeout_embed)
        
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