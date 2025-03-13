import random
import asyncio
import discord
from data_manager import server_data, get_user_data, save_data

# Sample trivia questions
TRIVIA_QUESTIONS = [
    {
        "question": "What is the name of the statue the Traveler touches in Mondstadt?",
        "answer": ["Anemo", "anemo statue", "statue of anemo", "anemo god statue"],
        "fact": "It's Dedicated to Barbatos, who shaped Mondstadt's freedom."
    },
    {
        "question": "What is the name of the region where the Traveler saves Paimon in Mondstadt?",
        "answer": ["Starfell Lake", "starfell lake", "the starfell lake", "lake"],
        "fact": "It is Named after a legend of lovers making a farewell promise."
    },
    {
        "question": "What gift does Amber give to the Traveler after they assist with the Hilichurl camp?",
        "answer": ["Wind Glider", "wind glider", "glider", "the wind glider"],
        "fact": "Wind Gliders are a symbol of Mondstadt's free spirit."
    },
    {
        "question": "Who is the Cavalry Captain of the Knights of Favonius?",
        "answer": ["Kaeya", "kaeya alberich", "cavalry captain kaeya", "captain kaeya"],
        "fact": "Kaeya is secretly a descendant of Khaenri'ah, He was left in Mondstadt by his father."
    },
    {
        "question": "What title does Jean grant to the Traveler?",
        "answer": ["Honorary Knight", "honorary knight", "the honorary knight", "knight"],
        "fact": "The title Honorary Knight was given to the Traveler as a sign of trust and recognition."
    },
    {
        "question": "Where does Venti tell the Traveler to meet him to save Dvalin?",
        "answer": ["Windrise", "the windrise", "at windrise", "to windrise"],
        "fact": "The big tree marks where Barbatos first blessed Mondstadt."
    },
    {
        "question": "What is the item Venti wants the Traveler to obtain from the Favonius Cathedral?",
        "answer": ["Holy Lyre der Himmel", "holy lyre", "lyre", "the lyre"],
        "fact": "A divine lyre Barbatos once played to bring peace."
    },
    {
        "question": "What is Venti's true identity?",
        "answer": ["Barbatos", "lord barbatos", "anemo archon", "the anemo archon"],
        "fact": "Once a small wind spirit, later freed Mondstadt."
    },
    {
        "question": "What do they do to the Teardrop Crystals to restore the lyre?",
        "answer": ["Purify", "purify them", "purification", "purify the crystals"],
        "fact": "Dvalin cried these tears because he was corrupted by Abyssal energy"
    },
    {
        "question": "Who rips the Gnosis out of Venti's chest?",
        "answer": ["Signora", "la signora", "the signora", "fair lady"],
        "fact": "Signora was once a normal Mondstadt woman named Rosalyne."
    },
    {
        "question": "Which Archon grants the Fatui Harbingers their power?",
        "answer": ["Tsaritsa", "the tsaritsa", "cryo archon", "the cryo archon"],
        "fact": "She leads the fatui."
    },
    {
        "question": "Who saves the Traveler from the Millelith?",
        "answer": ["Childe", "tartaglia", "ajax", "11th harbinger"],
        "fact": "He is deeply loyal to his family despite his involvement with the Fatui."
    },
    {
        "question": "Who is the first adeptus the Traveler meets in Jueyun Karst?",
        "answer": ["Moon Carver", "moon carver", "the moon carver", "mooncarver"],
        "fact": "An Adeptus in Jueyun Karst, one of Liyue's divine protectors"
    },
    {
        "question": "Where can the Demon Conqueror be found?",
        "answer": ["Wangshu Inn", "the wangshu inn", "at wangshu inn", "in wangshu inn"],
        "fact": "A quiet, peaceful inn in Liyue known for its healing properties."
    },
    {
        "question": "Where do they find Cloud Retainer?",
        "answer": ["Mt. Aocang", "mount aocang", "mountain aocang", "mt aocang"],
        "fact": "An intelligent adeptus on Mt. Aocang, known for her wisdom."
    },
    {
        "question": "To Whom does Childe introduce the Traveler and Paimon at Liuli Pavilion?",
        "answer": ["Zhongli", "mr zhongli", "consultant zhongli", "the consultant"],
        "fact": "Formerly known as Morax and the ruler of Liyue."
    },
    {
        "question": "Where do they find Madame Ping?",
        "answer": ["Yujing Terrace", "the yujing terrace", "at yujing terrace", "in yujing terrace"],
        "fact": "An elder Adeptus!"
    },
    {
        "question": "Who greets the Traveler and Paimon at Bubu Pharmacy?",
        "answer": ["Qiqi", "zombie qiqi", "little qiqi", "the zombie"],
        "fact": "A zombie, serving as a pharmacist."
    },
    {
        "question": "Who thanks the Traveler for taking care of Qiqi at the pharmacy?",
        "answer": ["Baizhu", "dr baizhu", "doctor baizhu", "the doctor"],
        "fact": "a skilled doctor and guardian of Qiqi"
    },
    {
        "question": "What powers does Childe unleash during the battle with the Traveler?",
        "answer": ["Foul Legacy", "foul legacy", "the foul legacy", "foul legacy transformation"],
        "fact": "Foul legacy is a form of Abyssal power"
    },
    {
        "question": "What does Ningguang sacrifice to defeat Osial?",
        "answer": ["The Jade Chamber", "jade chamber", "her jade chamber", "the floating palace"],
        "fact": "The jade chamber symbolizes her dominance in Liyue's economy."
    },
    {
        "question": "Who is the mysterious bard that helps the Traveler in Mondstadt?",
        "answer": ["Venti", "barbatos", "the bard", "windborne bard"],
        "fact": "Venti is the mortal vessel of Barbatos, the Anemo Archon."
    },
    {
        "question": "What is the name of the Geo Archon?",
        "answer": ["Zhongli", "morax", "rex lapis", "geo archon"],
        "fact": "Zhongli is the mortal vessel of Morax, the Geo Archon."
    },
    {
        "question": "Who is the leader of the Arataki Gang?",
        "answer": ["Itto", "arataki itto", "the one and oni", "gang leader itto"],
        "fact": "Itto is a Geo user and a descendant of the crimson oni."
    },
    {
        "question": "What is the name of the Electro Archon?",
        "answer": ["Raiden Shogun", "ei", "beelzebul", "electro archon"],
        "fact": "Raiden Shogun is the mortal vessel of Beelzebul, the Electro Archon."
    },
    {
        "question": "Who is the chief alchemist of the Knights of Favonius?",
        "answer": ["Albedo", "kreideprinz", "chief alchemist", "knights of favonius alchemist"],
        "fact": "Albedo is a synthetic human created by the alchemist Rhinedottir."
    },
    {
        "question": "What is the name of the organization led by Diluc?",
        "answer": ["Dawn Winery", "dawn winery", "winery", "dawn"],
        "fact": "Dawn Winery is the largest winery in Mondstadt, owned by Diluc."
    },
    {
        "question": "Who is the guardian yaksha that protects Liyue?",
        "answer": ["Xiao", "alatus", "vigilant yaksha", "guardian yaksha"],
        "fact": "Xiao is one of the five Yakshas dispatched by Morax to subdue demonic spirits."
    },
    {
        "question": "What is the name of the floating island above Inazuma?",
        "answer": ["Tenshukaku", "tenshukaku", "the tenshukaku", "inazuma castle"],
        "fact": "Tenshukaku is the residence of the Raiden Shogun in Inazuma."
    },
    {
        "question": "Who is the mysterious traveler from another world?",
        "answer": ["Aether", "Lumine", "the traveler", "traveler"],
        "fact": "The Traveler is searching for their lost sibling across Teyvat."
    },
    {
        "question": "What is the name of the organization that opposes the Vision Hunt Decree?",
        "answer": ["Resistance", "the resistance", "watatsumi army", "sangonomiya resistance"],
        "fact": "The Resistance is led by Sangonomiya Kokomi against the Raiden Shogun's Vision Hunt Decree."
    },
    {
        "question": "Who is the acting Grand Master of the Knights of Favonius?",
        "answer": ["Jean", "jean gunnhildr", "acting grand master", "knights of favonius leader"],
        "fact": "Jean is dedicated to maintaining peace and order in Mondstadt."
    },
    {
        "question": "What is the name of the dragon that terrorized Mondstadt?",
        "answer": ["Dvalin", "stormterror", "the dragon", "dragon of the east"],
        "fact": "Dvalin, also known as Stormterror, was once a protector of Mondstadt."
    },
    {
        "question": "Who is the mysterious Fatui Harbinger known for his icy demeanor?",
        "answer": ["Childe", "tartaglia", "ajax", "fatui harbinger"],
        "fact": "Childe is the 11th of the Fatui Harbingers and wields both Hydro and Electro powers."
    },
    {
        "question": "What is the name of the floating island above Liyue?",
        "answer": ["Jade Chamber", "jade chamber", "floating palace", "liyue palace"],
        "fact": "The Jade Chamber is a symbol of Ningguang's power and influence in Liyue."
    },
    {
        "question": "Who is the mysterious bard that helps the Traveler in Mondstadt?",
        "answer": ["Venti", "barbatos", "the bard", "windborne bard"],
        "fact": "Venti is the mortal vessel of Barbatos, the Anemo Archon."
    },
    {
        "question": "What is the name of the Geo Archon?",
        "answer": ["Zhongli", "morax", "rex lapis", "geo archon"],
        "fact": "Zhongli is the mortal vessel of Morax, the Geo Archon."
    },
    {
        "question": "Who is the leader of the Arataki Gang?",
        "answer": ["Itto", "arataki itto", "the one and oni", "gang leader itto"],
        "fact": "Itto is a Geo user and a descendant of the crimson oni."
    },
    {
        "question": "What is the name of the Electro Archon?",
        "answer": ["Raiden Shogun", "ei", "beelzebul", "electro archon"],
        "fact": "Raiden Shogun is the mortal vessel of Beelzebul, the Electro Archon."
    },
    {
        "question": "Who is the chief alchemist of the Knights of Favonius?",
        "answer": ["Albedo", "kreideprinz", "chief alchemist", "knights of favonius alchemist"],
        "fact": "Albedo is a synthetic human created by the alchemist Rhinedottir."
    },
    {
        "question": "What is the name of the organization led by Diluc?",
        "answer": ["Dawn Winery", "dawn winery", "winery", "dawn"],
        "fact": "Dawn Winery is the largest winery in Mondstadt, owned by Diluc."
    },
    {
        "question": "Who is the guardian yaksha that protects Liyue?",
        "answer": ["Xiao", "alatus", "vigilant yaksha", "guardian yaksha"],
        "fact": "Xiao is one of the five Yakshas dispatched by Morax to subdue demonic spirits."
    },
    {
        "question": "What is the name of the floating island above Inazuma?",
        "answer": ["Tenshukaku", "tenshukaku", "the tenshukaku", "inazuma castle"],
        "fact": "Tenshukaku is the residence of the Raiden Shogun in Inazuma."
    },
    {
        "question": "What is the name of the artifact set that boosts Pyro damage?",
        "answer": ["Crimson Witch of Flames", "crimson witch", "crimson witch of flames set", "pyro set"],
        "fact": "The Crimson Witch of Flames set is favored by Pyro characters for its damage boost."
    },
    {
        "question": "Which character is known as the 'Kätzlein Cocktail'?",
        "answer": ["Diona", "diona kätzlein", "kätzlein cocktail", "bartender diona"],
        "fact": "Diona is a bartender at the Cat's Tail and is known for her unique drinks."
    },
    {
        "question": "What is the name of the Electro Archon's signature weapon?",
        "answer": ["Engulfing Lightning", "engulfing lightning", "raiden shogun's polearm", "electro archon weapon"],
        "fact": "The Engulfing Lightning is a polearm that increases Energy Recharge and ATK."
    },
    {
        "question": "Who is the librarian of the Knights of Favonius?",
        "answer": ["Lisa", "lisa minci", "librarian lisa", "knights of favonius librarian"],
        "fact": "Lisa is an Electro user and a graduate of Sumeru Academia."
    },
    {
        "question": "What is the name of the city ruled by the Anemo Archon?",
        "answer": ["Mondstadt", "mondstadt", "city of freedom", "anemo city"],
        "fact": "Mondstadt is known as the City of Freedom and is protected by the Anemo Archon, Barbatos."
    },
    {
        "question": "Which character is known as the 'Chivalric Blossom'?",
        "answer": ["Eula", "eula lawrence", "chivalric blossom", "spindrift knight"],
        "fact": "Eula is a descendant of the Lawrence Clan and serves as the Spindrift Knight in the Knights of Favonius."
    }
]

async def play_trivia(channel):
    """A trivia game with free-form answers and unlimited attempts."""
    try:
        # Select random question
        question_data = random.choice(TRIVIA_QUESTIONS)
        correct_answers = [ans.lower() for ans in question_data["answer"]]
        
        # Create question embed
        question_embed = discord.Embed(
            title="🎯  Trivia Time!",
            description=question_data["question"],
            color=0x9b59b6  # Purple color
        )
        question_embed.set_footer(text="You have 30 seconds to answer! Just type your answer in the chat.")
        
        await channel.send(embed=question_embed)

        # Get bot instance
        bot = channel.guild.me._state._get_client()
        
        # Track all users who attempted
        attempted_users = {}
        
        def check(msg):
            return (
                msg.channel.id == channel.id and
                not msg.author.bot and
                msg.content.lower().strip() in correct_answers
            )

        end_time = asyncio.get_event_loop().time() + 30
        while asyncio.get_event_loop().time() < end_time:
            try:
                remaining_time = max(0.1, end_time - asyncio.get_event_loop().time())
                msg = await bot.wait_for('message', check=check, timeout=remaining_time)
                
                # Process the answer
                user = msg.author
                user_answer = msg.content.lower().strip()
                
                # Track this attempt
                if user.id not in attempted_users:
                    attempted_users[user.id] = []
                attempted_users[user.id].append(user_answer)
                
                # Correct answer embed
                winner_embed = discord.Embed(
                    title="✨ Correct Answer!",
                    description=f"Well done {user.mention}!\nYou got it right with: {user_answer}",
                    color=0x2ecc71  # Green color
                )
                winner_embed.add_field(
                    name="Fun Fact",
                    value=question_data["fact"],
                    inline=False
                )
                winner_embed.add_field(
                    name="Prize",
                    value="You win 100 <a:Rubles:1344705820222292011>!",
                    inline=False
                )
                await channel.send(embed=winner_embed)
                
                # Award currency
                user_data = get_user_data(str(channel.guild.id), str(user.id))
                user_data["currency"] += 100
                save_data(server_data)
                return
                
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
        
        # Add participation summary
        if attempted_users:
            participation = []
            for user_id, answers in attempted_users.items():
                user = channel.guild.get_member(user_id)
                if user:
                    participation.append(f"{user.mention}: {len(answers)} attempts")
            timeout_embed.add_field(
                name="Participation Summary",
                value="\n".join(participation),
                inline=False
            )
        else:
            timeout_embed.add_field(
                name="Participation",
                value="Nobody attempted to answer 😢",
                inline=False
            )
        
        await channel.send(embed=timeout_embed)
        
    except Exception as e:
        print(f"DEBUG: Game error: {e}")
        error_embed = discord.Embed(
            title="<a:Animated_Cross:1344705833627549748> Error",
            description="An error occurred in the game. Please try again.",
            color=0xff0000  # Red color
        )
        try:
            await channel.send(embed=error_embed)
        except:
            pass