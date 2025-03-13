import random
import asyncio
import discord
from discord.ui import Button, View
from data_manager import server_data, get_user_data, save_data

class BattleRoyaleView(View):
    def __init__(self, original_message):
        super().__init__(timeout=None)  # No timeout to prevent button issues
        self.players = set()
        self.original_message = original_message
        self.countdown_task = None
        self.is_running = False
        self.seconds_remaining = 10  # Track remaining seconds directly
        
        join_button = Button(
            style=discord.ButtonStyle.danger,
            label="Join Battle!",
            emoji="⚔️",
            custom_id="join"
        )
        join_button.callback = self.join_callback
        self.add_item(join_button)
    
    def create_embed(self, seconds_left):
        reward_text = (
            "🥇 1st Place: 150 rubles\n"
            "🥈 2nd Place: 100 rubles\n"
            "🥉 3rd Place: 50 rubles\n"
            "❌ Others: -100 rubles\n\n"
            "*Rewards adjust based on player count*"
        )
        
        return discord.Embed(
            title="🏆 Battle Royale Tournament!",
            description=(
                f"⏰ **{seconds_left} seconds remaining to join!**\n\n"
                f"Current Contestants: {len(self.players)}\n\n"
                f"**Rewards:**\n{reward_text}\n\n"
                "Click the button to enter the battle!"
            ),
            color=0xff0000
        ).set_footer(text="May the odds be ever in your favor!")
    
    async def start_countdown(self):
        self.is_running = True
        self.seconds_remaining = 10
        try:
            for seconds_left in range(10, -1, -1):
                if not self.is_running:
                    break
                self.seconds_remaining = seconds_left  # Update the class variable
                embed = self.create_embed(seconds_left)
                await self.original_message.edit(embed=embed)
                await asyncio.sleep(1)
        except Exception as e:
            print(f"DEBUG: Countdown error: {e}")
        finally:
            self.is_running = False
    
    async def join_callback(self, interaction: discord.Interaction):
        if not self.is_running:
            await interaction.response.send_message(
                "This battle is no longer accepting new players!", 
                ephemeral=True
            )
            return

        user_id = interaction.user.id
        if user_id in self.players:
            await interaction.response.send_message(
                "You're already in the battle!", 
                ephemeral=True
            )
            return
            
        self.players.add(user_id)
        
        # Use the class variable to track remaining time instead of accessing the task
        embed = self.create_embed(self.seconds_remaining)
        await self.original_message.edit(embed=embed)
        
        await interaction.response.send_message(
            "You've joined the battle! Prepare yourself!", 
            ephemeral=True
        )

class BattleRoyale:
    def __init__(self, channel, players):
        self.channel = channel
        self.players = list(players)
        self.alive_players = self.players.copy()
        self.eliminated_order = []
        self.kill_messages = [
            "{attacker} slayed {victim} with a mighty blow! ⚔️",
            "{attacker} ambushed {victim} and struck them down! 🗡️",
            "{attacker} outmaneuvered {victim} and delivered the final blow! 🏹",
            "{attacker} unleashed a flurry of attacks on {victim}! 🌀",
            "{attacker}'s strategy outsmarted {victim}! 🎯",
            "{attacker}'s special skill defeated {victim}! 🌟",
            "{attacker}'s critical hit took {victim} by surprise! 🔥",
            "{attacker}'s swift strike finished off {victim}! 💨",
            "{attacker}'s powerful attack overwhelmed {victim}! 💥",
            "{attacker}'s spaceship blasted {victim}'s ship into pieces! 🚀",
            "{attacker}'s laser cannon obliterated {victim}'s defenses! 🔫",
            "{attacker} boarded {victim}'s ship and took control! 🏴‍☠️",
            "{attacker}'s drone swarm overwhelmed {victim}'s ship! 🛸",
            "{attacker}'s asteroid maneuver smashed {victim}'s ship! ☄️",
            "{attacker}'s alien allies vaporized {victim}'s crew! 👽",
            "{attacker}'s stealth ship ambushed {victim}'s vessel! 🌌"
        ]
        self.self_kill_messages = [
            "{player} accidentally fell on their own sword! ⚔️",
            "{player} tripped and fell, knocking themselves out! 💀",
            "{player}'s weapon backfired and injured themselves! 💥",
            "{player} got lost and couldn't find their way back! 🧭",
            "{player}'s trap caught themselves instead! 🪤",
            "{player}'s spell misfired and hit themselves! 🔮",
            "{player} got distracted and hurt themselves! 😵",
            "{player} tripped over their own cape and fell! 🦸",
            "{player}'s power backfired and hurt themselves! 💥",
            "{player} got distracted and was knocked out! 😵",
            "{player}'s weapon malfunctioned, causing self-injury! 🔫",
            "{player}'s ship malfunctioned and exploded! 💥",
            "{player}'s crew mutinied and took over the ship! 🛳️",
            "{player}'s navigation system failed, crashing into an asteroid! 🌑",
            "{player}'s ship got sucked into a black hole! 🕳️",
            "{player}'s reactor core overheated and blew up! 🔥"
        ]
    
    async def run_battle(self):
        round_num = 1
        
        while len(self.alive_players) > 1:
            await asyncio.sleep(2)
            
            round_embed = discord.Embed(
                title=f"Round {round_num}",
                description=f"Survivors remaining: {len(self.alive_players)}",
                color=0xff0000
            )
            
            events = []
            num_events = min(3, max(1, len(self.alive_players) // 2))
            
            for _ in range(num_events):
                if len(self.alive_players) < 2:
                    break
                    
                if random.random() < 0.3:
                    # Self elimination
                    victim = random.choice(self.alive_players)
                    self.alive_players.remove(victim)
                    self.eliminated_order.append(victim)
                    events.append(random.choice(self.self_kill_messages).format(
                        player=f"<@{victim}>"
                    ))
                else:
                    # Player vs player elimination
                    killer = random.choice(self.alive_players)
                    possible_victims = [p for p in self.alive_players if p != killer]
                    
                    if possible_victims:
                        victim = random.choice(possible_victims)
                        self.alive_players.remove(victim)
                        self.eliminated_order.append(victim)
                        events.append(random.choice(self.kill_messages).format(
                            attacker=f"<@{killer}>",
                            victim=f"<@{victim}>"
                        ))
            
            if events:
                round_embed.add_field(
                    name="Round Events",
                    value="\n".join(events),
                    inline=False
                )
                await self.channel.send(embed=round_embed)
            
            round_num += 1
        
        # Add winner to eliminated_order
        if self.alive_players:
            self.eliminated_order.append(self.alive_players[0])
        
        await self.distribute_rewards()

    async def distribute_rewards(self):
        try:
            total_players = len(self.players)
            eliminated_order = list(reversed(self.eliminated_order))
            
            rewards_embed = discord.Embed(
                title="🏆 Battle Royale Results!",
                color=0xffd700
            )

            if total_players < 2:
                rewards_embed.description = "Not enough players participated!"
                await self.channel.send(embed=rewards_embed)
                return
                
            guild_id = str(self.channel.guild.id)
            
            if total_players == 2:
                winner_id, loser_id = eliminated_order[:2]
                
                winner_data = get_user_data(guild_id, str(winner_id))
                loser_data = get_user_data(guild_id, str(loser_id))
                
                winner_data["currency"] = winner_data.get("currency", 0) + 50
                loser_data["currency"] = loser_data.get("currency", 0) - 100
                
                rewards_embed.description = (
                    f"🥇 Winner: <@{winner_id}> (+50 rubles)\n"
                    f"<a:Animated_Cross:1344705833627549748> Loser: <@{loser_id}> (-100 rubles)"
                )
                
            elif total_players == 3:
                winner_id, second_id, third_id = eliminated_order[:3]
                
                winner_data = get_user_data(guild_id, str(winner_id))
                second_data = get_user_data(guild_id, str(second_id))
                third_data = get_user_data(guild_id, str(third_id))
                
                winner_data["currency"] = winner_data.get("currency", 0) + 100
                second_data["currency"] = second_data.get("currency", 0) + 50
                third_data["currency"] = third_data.get("currency", 0) - 100
                
                rewards_embed.description = (
                    f"🥇 1st Place: <@{winner_id}> (+100 rubles)\n"
                    f"🥈 2nd Place: <@{second_id}> (+50 rubles)\n"
                    f"<a:Animated_Cross:1344705833627549748> 3rd Place: <@{third_id}> (-100 rubles)"
                )
                
            else:
                top_3 = eliminated_order[:3]
                rewards = {0: 150, 1: 100, 2: 50}
                
                results_text = []
                
                # Handle winners
                for place, player_id in enumerate(top_3):
                    player_data = get_user_data(guild_id, str(player_id))
                    player_data["currency"] = player_data.get("currency", 0) + rewards[place]
                    
                    medal = ["🥇", "🥈", "🥉"][place]
                    place_text = ["1st", "2nd", "3rd"][place]
                    results_text.append(f"{medal} {place_text} Place: <@{player_id}> (+{rewards[place]} rubles)")
                
                # Handle losers
                for player_id in eliminated_order[3:]:
                    player_data = get_user_data(guild_id, str(player_id))
                    player_data["currency"] = player_data.get("currency", 0) - 100
                
                results_text.append(f"\n💀 All other participants lost 100 rubles!")
                rewards_embed.description = "\n".join(results_text)
            
            save_data(server_data)
            
            rewards_embed.add_field(
                name="Battle Statistics",
                value=f"Total Participants: {total_players}\nTotal Rounds: {len(self.eliminated_order)}",
                inline=False
            )
            
            await self.channel.send(embed=rewards_embed)
            
        except Exception as e:
            print(f"Error distributing rewards: {e}")
            await self.channel.send("An error occurred while distributing rewards!")

async def start_battle_royale(channel):
    """Starts a battle royale game in the specified channel."""
    try:
        initial_embed = discord.Embed(
            title="🏆 Battle Royale Tournament!",
            description=(
                "⏰ **10 seconds remaining to join!**\n\n"
                "Current Contestants: 0\n\n"
                "**Rewards:**\n"
                "🥇 1st Place: 150 rubles\n"
                "🥈 2nd Place: 100 rubles\n"
                "🥉 3rd Place: 50 rubles\n"
                "<a:Animated_Cross:1344705833627549748> Others: -100 rubles\n\n"
                "*Rewards adjust based on player count*\n\n"
                "Click the button to enter the battle!"
            ),
            color=0xff0000
        )
        initial_embed.set_footer(text="May the odds be ever in your favor!")
        
        message = await channel.send(embed=initial_embed)
        view = BattleRoyaleView(message)
        await message.edit(view=view)
        
        # Start countdown
        await view.start_countdown()
        
        if len(view.players) < 2:
            not_enough_embed = discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Battle Royale Cancelled",
                description="Not enough players joined the battle!",
                color=0x95a5a6
            )
            await message.edit(embed=not_enough_embed, view=None)
            return
        
        battle = BattleRoyale(channel, view.players)
        
        starting_embed = discord.Embed(
            title="⚔️ Battle Royale Beginning!",
            description=f"**{len(view.players)} warriors** enter the arena!\n\nLet the battle begin!",
            color=0xff0000
        )
        await channel.send(embed=starting_embed)
        
        await battle.run_battle()
        
    except Exception as e:
        print(f"DEBUG: Game error: {e}")
        error_embed = discord.Embed(
            title="<a:Animated_Cross:1344705833627549748> Error",
            description="An error occurred in the game. Please try again.",
            color=0xff0000
        )
        await channel.send(embed=error_embed)