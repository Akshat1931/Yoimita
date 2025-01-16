import importlib
import os
import random
import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import math
import aiohttp
from PIL import Image, ImageDraw, ImageFont
import io
from asyncio import sleep
import random

# At the top with your other imports:
from data_manager import server_data, get_user_data, save_data
from games.guess_the_number import play_guess_the_number
from games.trivia import play_trivia
from games.coin import play_coinflip

# Then modify your RANDOM_EVENTS list:

LOADED_GAMES = {}

# Function to load all games dynamically
def load_games():
    global LOADED_GAMES
    games_dir = "games"
    for filename in os.listdir(games_dir):
        if filename.endswith(".py"):
            module_name = filename[:-3]
            module = importlib.import_module(f"{games_dir}.{module_name}")
            LOADED_GAMES[module_name] = module

# Call this function at the start of your bot
load_games()

with open("config.json", "r") as config_file:
    config = json.load(config_file)

BOT_TOKEN = config["bot_token"]
BOT_OWNER_ID = int(config["owner_id"])

RANDOM_EVENTS = [
    play_coinflip,
    play_guess_the_number,  # Reference the game function
    play_trivia
]


RANDOM_CHANNELS = {}

intents = discord.Intents.all()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="/", intents=intents)
data_file = "server_user_data.json"



def exp_to_next_level(level):
    return 100 * math.pow(1.8, level - 1)

def calculate_currency(level):
    return int(50 * (1.00 ** (level - 1)))



@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    server_id = str(message.guild.id)
    user_id = str(message.author.id)
    user = get_user_data(server_id, user_id)
    
    user["exp"] += 3

    if user["exp"] >= exp_to_next_level(user["level"]):
        user["exp"] -= exp_to_next_level(user["level"])
        user["level"] += 1
        reward = calculate_currency(user["level"])
        user["currency"] += reward
        await message.channel.send(f"🎉 {message.author.mention} leveled up to Level {user['level']} and earned {reward} <a:rubles:1329009278811373740>!")

    save_data(server_data)  # Make sure we save after any changes
    await bot.process_commands(message) 




@tasks.loop(minutes=10)
async def random_event():
    print("Random event loop triggered")  # Debug print
    for guild_id, channel_id in RANDOM_CHANNELS.items():
        try:
            channel = bot.get_channel(int(channel_id))  # Make sure channel_id is converted to int
            if channel:
                print(f"Sending event to channel {channel.name}")  # Debug print
                # Send warning message
                warning_msg = await channel.send("⚠️ A random event is approaching in 5 seconds! ⚠️")
                await sleep(5)  # Wait 5 seconds
                
                # Send the actual event
                event_message = random.choice(RANDOM_EVENTS)
                await channel.send(f"🎉 **Random Event!** 🎉\n{event_message}")
                
                # Delete the warning message (optional)
                await warning_msg.delete()
        except Exception as e:
            print(f"Error in random event for guild {guild_id}: {e}")

# Update the set_event_channel command to ensure proper storage
@bot.tree.command(name="set_event_channel", description="Set the current channel for random events")
async def set_event_channel(interaction: discord.Interaction):
    try:
        RANDOM_CHANNELS[str(interaction.guild_id)] = interaction.channel_id
        print(f"Set event channel for guild {interaction.guild_id}: {interaction.channel_id}")  # Debug print
        await interaction.response.send_message("✅ This channel has been set for random events!", ephemeral=True)
        
        # Test message to verify channel is working
        channel = bot.get_channel(interaction.channel_id)
        if channel:
            await channel.send("🎯 Random events will now appear in this channel!")
    except Exception as e:
        await interaction.response.send_message(f"Error setting event channel: {e}", ephemeral=True)

@bot.tree.command(name="remove_event_channel", description="Remove the random events channel")
@commands.has_permissions(administrator=True)
async def remove_event_channel(interaction: discord.Interaction):
    if str(interaction.guild_id) in RANDOM_CHANNELS:
        del RANDOM_CHANNELS[str(interaction.guild_id)]
        await interaction.response.send_message("Random events channel has been removed!", ephemeral=True)
    else:
        await interaction.response.send_message("No event channel was set!", ephemeral=True)

# Add this new command to force trigger an event (for testing)
@bot.tree.command(name="test_event", description="Trigger a test event")
@app_commands.default_permissions(administrator=True)
async def test_event(interaction: discord.Interaction):
    try:
        channel_id = RANDOM_CHANNELS.get(str(interaction.guild_id))
        if not channel_id:
            await interaction.response.send_message("No event channel set. Use /set_event_channel first!", ephemeral=True)
            return
            
        channel = bot.get_channel(int(channel_id))
        if not channel:
            await interaction.response.send_message("Could not find the event channel. Please set it again.", ephemeral=True)
            return

        await interaction.response.send_message("Starting event...", ephemeral=True)
        
        # Send warning
        await channel.send("⚠️ Event starting in 5 seconds! ⚠️")
        await sleep(5)  # Make sure asyncio is imported at the top of your main bot file
        
        # Start event
        event = random.choice(RANDOM_EVENTS)
        if callable(event):
            await event(channel)
        else:
            await channel.send(f"🎉 **Event!** 🎉\n{event}")
        
    except Exception as e:
        print(f"Error in test_event: {e}")
        await interaction.followup.send("An error occurred. Please try again.", ephemeral=True)
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
        random_event.start()  # Start the random event loop
        print("Random event loop started.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.tree.command(name="balance", description="Check your currency balance.")
async def balance(interaction: discord.Interaction):
    user = get_user_data(interaction.guild_id, interaction.user.id)
    currency = user["currency"]
    
    embed = discord.Embed(
        title="Your Balance",
        description=f"**{interaction.user.name}'s Currency:** {currency} <a:rubles:1329009278811373740>",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="profile", description="View your profile.")
async def profile(interaction: discord.Interaction):
    user = get_user_data(interaction.guild_id, interaction.user.id)
    level = user["level"]
    exp = user["exp"]
    next_level_exp = exp_to_next_level(level)
    progress = (exp / next_level_exp) * 100

    embed = discord.Embed(
        title=f"{interaction.user.name}'s Profile",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=interaction.user.avatar.url)
    embed.add_field(name="Level", value=str(level), inline=False)
    embed.add_field(name="Overall Currency", value=f"{user['currency']} <a:rubles:1329009278811373740>", inline=False)
    embed.add_field(
        name="Progress to Next Level",
        value=f"{progress:.2f}% ({exp}/{next_level_exp:.0f} EXP)",
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="fine", description="Fine a user an amount of currency.")
@app_commands.describe(user="The user to fine.", amount="The amount to fine.")
async def fine(interaction: discord.Interaction, user: discord.User, amount: int):
    if interaction.user.id != BOT_OWNER_ID:
        await interaction.response.send_message("Only the bot owner can use this command.", ephemeral=True)
        return

    if amount <= 0:
        await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
        return

    user_data = get_user_data(interaction.guild_id, user.id)
    user_data["currency"] -= amount
    save_data(server_data)
    await interaction.response.send_message(f"{user.name} has been fined {amount} <a:rubles:1329009278811373740>.")

@bot.tree.command(name="pay", description="Pay another user an amount of currency.")
@app_commands.describe(user="The user to pay.", amount="The amount to pay.")
async def pay(interaction: discord.Interaction, user: discord.User, amount: int):
    if amount <= 0:
        await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
        return

    payer_data = get_user_data(interaction.guild_id, interaction.user.id)
    
    if payer_data["currency"] < amount:
        await interaction.response.send_message("You do not have enough currency to make this payment.", ephemeral=True)
        return

    recipient_data = get_user_data(interaction.guild_id, user.id)
    
    payer_data["currency"] -= amount
    recipient_data["currency"] += amount
    save_data(server_data)

    await interaction.response.send_message(f"You have paid {amount} <a:rubles:1329009278811373740> to {user.name}.")

@bot.tree.command(name="give", description="Give another user an amount of currency without deducting from your balance.")
@app_commands.describe(user="The user to give currency to.", amount="The amount to give.")
async def give(interaction: discord.Interaction, user: discord.User, amount: int):
    if interaction.user.id != BOT_OWNER_ID:
        await interaction.response.send_message("Only the bot owner can use this command.", ephemeral=True)
        return

    if amount <= 0:
        await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
        return

    recipient_data = get_user_data(interaction.guild_id, user.id)
    recipient_data["currency"] += amount
    save_data(server_data)
    await interaction.response.send_message(f"You have given {amount} <a:rubles:1329009278811373740> to {user.name}.")


@bot.tree.command(name="upload_background", description="Upload a custom background for your level card")
async def upload_background(interaction: discord.Interaction, image: discord.Attachment):
    try:
        # Check if the uploaded file is an image
        if not image.content_type.startswith('image/'):
            await interaction.response.send_message("Please upload an image file.", ephemeral=True)
            return

        # Check file size (limit to 5MB)
        if image.size > 5 * 1024 * 1024:
            await interaction.response.send_message("Image file size must be under 5MB.", ephemeral=True)
            return

        # Get user data using the same method as level command
        user = get_user_data(interaction.guild_id, interaction.user.id)

        
        # Store the image URL
        user["background_url"] = image.url
        
        # Save the updated user data
        save_data(server_data)
       

        await interaction.response.send_message("Background image updated successfully! Use /level to see your new card.", ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="remove_background", description="Remove your custom background")
async def remove_background(interaction: discord.Interaction):
    try:
        # Get user data using the same method as level command
        user = get_user_data(interaction.guild_id, interaction.user.id)
        
        # Check if user has a background set
        if not user.get("background_url"):
            await interaction.response.send_message("You don't have a custom background set.", ephemeral=True)
            return
        
        # Remove background
        user["background_url"] = None
        
        # Save the updated user data
        save_data(server_data)
        
        await interaction.response.send_message("Background removed successfully! Your level card will now use the default background.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

# ... (previous code remains the same until the level command)

@bot.tree.command(name="level", description="Check your level and progress.")
async def level(interaction: discord.Interaction):
    try:
        await interaction.response.send_message("Generating level card...")
    except:
        return

    user = get_user_data(interaction.guild_id, interaction.user.id)
    level = user["level"]
    exp = int(user["exp"])
    next_level_exp = int(exp_to_next_level(level))
    progress = min(max(exp / next_level_exp if next_level_exp > 0 else 0, 0), 1)

    width, height = 600, 300
    background_color = (22, 27, 34)
    accent_color = (88, 166, 255)
    bar_color = accent_color
    bar_background = (47, 54, 61)
    text_color = (255, 255, 255)
    secondary_text_color = (139, 148, 158)

    # Create base image
    image = Image.new("RGBA", (width, height), color=(0, 0, 0, 0))
    
    # Load custom background if available
    if user.get("background_url"):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(user["background_url"]) as response:
                    background_data = await response.read()
                    background_image = Image.open(io.BytesIO(background_data))
                    
                    # Resize background to fit card dimensions
                    background_image = background_image.convert('RGBA')
                    background_image = background_image.resize((width, height), Image.Resampling.LANCZOS)
                    
                    # Add slight darkening overlay for better text visibility
                    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 128))
                    background_image = Image.alpha_composite(background_image, overlay)
                    
                    image = background_image
        except Exception as e:
            print(f"Error loading background: {e}")
            # Fall back to default background if custom background fails
            draw = ImageDraw.Draw(image)
            for y in range(height):
                r = int(32 + (22 - 32) * y / height)
                g = int(37 + (27 - 37) * y / height)
                b = int(44 + (34 - 44) * y / height)
                draw.line([(0, y), (width, y)], fill=(r, g, b))
    else:
        # Use default background
        draw = ImageDraw.Draw(image)
        for y in range(height):
            r = int(32 + (22 - 32) * y / height)
            g = int(37 + (27 - 37) * y / height)
            b = int(44 + (34 - 44) * y / height)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

    draw = ImageDraw.Draw(image)
    # Add grid pattern
    for i in range(0, width, 20):
        draw.line([(i, 0), (i, height)], fill=(255, 255, 255, 10))
    for i in range(0, height, 20):
        draw.line([(0, i), (width, i)], fill=(255, 255, 255, 10))

    # Create avatar glow
    avatar_glow_size = 120
    avatar_glow = Image.new('RGBA', (avatar_glow_size, avatar_glow_size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(avatar_glow)
    for i in range(10):
        alpha = int(100 - i * 10)
        glow_draw.ellipse([i, i, avatar_glow_size-i, avatar_glow_size-i], 
                         fill=(accent_color[0], accent_color[1], accent_color[2], alpha))
    image.paste(avatar_glow, (30, 20), avatar_glow)

    # Get and process avatar
    try:
        avatar_size = 100
        avatar_url = str(interaction.user.display_avatar.replace(size=256).url)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as response:
                avatar_data = await response.read()
                avatar_image = Image.open(io.BytesIO(avatar_data))
        
        avatar_image = avatar_image.convert('RGBA')
        avatar_image = avatar_image.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
        
        # Create circular mask
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, avatar_size - 1, avatar_size - 1), fill=255)
        
        # Apply mask to avatar
        output = Image.new('RGBA', (avatar_size, avatar_size), (0, 0, 0, 0))
        output.paste(avatar_image, (0, 0))
        output.putalpha(mask)
        
        image.alpha_composite(output, (40, 30))
    except Exception as e:
        print(f"Avatar loading error: {e}")
        draw.ellipse([40, 30, 140, 130], fill=(47, 54, 61))

    # Load fonts
    try:
        font = ImageFont.truetype("arial.ttf", 24)
        title_font = ImageFont.truetype("arial.ttf", 40)
        small_font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
        title_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Draw username and decorative line
    username = interaction.user.name
    draw.text((170, 40), username, font=title_font, fill=text_color)
    draw.line([(170, 90), (550, 90)], fill=accent_color, width=2)

    # Helper function for rounded rectangles with border
    def draw_rounded_rect_with_border(x, y, w, h, radius, fill_color, border_color, border_width=2):
        # Draw the background
        draw_rounded_rect(x, y, w, h, radius, fill_color)
        
        # Draw the border
        for i in range(border_width):
            # Top line
            draw.line([(x + radius, y + i), (x + w - radius, y + i)], fill=border_color)
            # Bottom line
            draw.line([(x + radius, y + h - i - 1), (x + w - radius, y + h - i - 1)], fill=border_color)
            # Left line
            draw.line([(x + i, y + radius), (x + i, y + h - radius)], fill=border_color)
            # Right line
            draw.line([(x + w - i - 1, y + radius), (x + w - i - 1, y + h - radius)], fill=border_color)
        
        # Draw the rounded corners
        for i in range(border_width):
            draw.arc([x + i, y + i, x + radius * 2 - i, y + radius * 2 - i], 180, 270, fill=border_color)
            draw.arc([x + w - radius * 2 + i, y + i, x + w - i, y + radius * 2 - i], 270, 360, fill=border_color)
            draw.arc([x + i, y + h - radius * 2 + i, x + radius * 2 - i, y + h - i], 90, 180, fill=border_color)
            draw.arc([x + w - radius * 2 + i, y + h - radius * 2 + i, x + w - i, y + h - i], 0, 90, fill=border_color)

    # Helper function for basic rounded rectangles
    def draw_rounded_rect(x, y, w, h, radius, color):
        draw.rectangle([x+radius, y, x+w-radius, y+h], fill=color)
        draw.rectangle([x, y+radius, x+w, y+h-radius], fill=color)
        draw.ellipse([x, y, x+radius*2, y+radius*2], fill=color)
        draw.ellipse([x+w-radius*2, y, x+w, y+radius*2], fill=color)
        draw.ellipse([x, y+h-radius*2, x+radius*2, y+h], fill=color)
        draw.ellipse([x+w-radius*2, y+h-radius*2, x+w, y+h], fill=color)

    box_width = 130
    box_height = 55
    box_spacing = 20

    # Helper function to center text in a box
    def get_centered_position(text, box_x, box_width, font):
        text_width = draw.textlength(text, font=font)
        return box_x + (box_width - text_width) / 2

    # Rank box - Centered text
    rank_x = 170
    rank_y = 120
    draw_rounded_rect_with_border(rank_x, rank_y, box_width, box_height, 10, (47, 54, 61), accent_color)
    
    # Center "RANK" text
    rank_label_x = get_centered_position("RANK", rank_x, box_width, small_font)
    draw.text((rank_label_x, rank_y + 5), "RANK", font=small_font, fill=secondary_text_color)
    
    # Center rank number
    rank_number = f"#{level + 1}"
    rank_number_x = get_centered_position(rank_number, rank_x, box_width, font)
    draw.text((rank_number_x, rank_y + 22), rank_number, font=font, fill=text_color)

    # Level box - Centered text
    level_x = rank_x + box_width + box_spacing
    level_y = rank_y
    draw_rounded_rect_with_border(level_x, level_y, box_width, box_height, 10, (47, 54, 61), accent_color)
    
    # Center "LEVEL" text
    level_label_x = get_centered_position("LEVEL", level_x, box_width, small_font)
    draw.text((level_label_x, level_y + 5), "LEVEL", font=small_font, fill=secondary_text_color)
    
    # Center level number
    level_number = str(level)
    level_number_x = get_centered_position(level_number, level_x, box_width, font)
    draw.text((level_number_x, level_y + 22), level_number, font=font, fill=text_color)

    # Progress bar
    bar_width = 380
    bar_height = 30
    bar_x = 170
    bar_y = 220
    
    # Experience text
    draw.text((bar_x, bar_y - 35), "EXPERIENCE", font=small_font, fill=secondary_text_color)
    
    # XP Text
    xp_text = f"{exp}/{next_level_exp} XP"
    text_width = draw.textlength(xp_text, font=small_font)
    draw.text((bar_x + bar_width - text_width, bar_y - 35), xp_text, font=small_font, fill=text_color)
    
    # Background bar
    draw_rounded_rect(bar_x, bar_y, bar_width, bar_height, 15, bar_background)
    
    # Progress bar
    if progress > 0:
        progress_width = int(bar_width * progress)
        if progress_width > 30:
            draw_rounded_rect(bar_x, bar_y, progress_width, bar_height, 15, bar_color)

    # Add corner accents
    corner_size = 20
    accent_color_transparent = (accent_color[0], accent_color[1], accent_color[2], 100)
    
    draw.line([(0, corner_size), (0, 0), (corner_size, 0)], fill=accent_color_transparent, width=2)
    draw.line([(width-corner_size, 0), (width, 0), (width, corner_size)], fill=accent_color_transparent, width=2)
    draw.line([(0, height-corner_size), (0, height), (corner_size, height)], fill=accent_color_transparent, width=2)
    draw.line([(width-corner_size, height), (width, height), (width, height-corner_size)], fill=accent_color_transparent, width=2)

    # Save and send the image
    with io.BytesIO() as image_binary:
        image.save(image_binary, 'PNG')
        image_binary.seek(0)
        file = discord.File(fp=image_binary, filename='level.png')
        
        try:
            await interaction.edit_original_response(content=None, attachments=[file])
        except discord.NotFound:
            try:
                await interaction.followup.send(file=file)
            except:
                pass

bot.run(BOT_TOKEN)