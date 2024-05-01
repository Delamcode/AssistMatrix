import aiohttp
import discord
import json
from dotenv import load_dotenv
import os
import traceback
import datetime

load_dotenv()

version = "v1"

# --------- TOKENS ---------
bot_token = os.environ['BOT_KEY']
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
PROXY_URL = os.getenv('PROXY_URL')


user_history = {}
bot = discord.Bot(intents=discord.Intents.default())



async def meta(message, bot):
    attached_all = ""
    attachments = []
    if message.attachments:
        for attachment in message.attachments:
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as response:
                    if response.status == 200:
                        attached = await response.read()
                    else:
                        attached =  None
            try:
                decoded = attached.content.decode('utf-8')
                attachments.append(f"File \"{attachment.filename}\" is attached: {decoded} End of file \"{attachment.filename}\"")
            except UnicodeDecodeError:
                pass
        attached_all = ''.join(attachments)
    mention = f'<@{bot.user.id}>'
    if message.content == mention:
        msg_content = 'Introduce yourself as AssistMatrix, a discord bot. Do not make stuff up about your capabillites as a discord bot. You are able to respond to messages after being pinged, or generate images with the ```/imagine``` command.'
    else:
        msg_content = message.content.replace(mention, '').strip()
    if attached_all:
        msg_content = f"{msg_content} ATTACHMENTS: {attached_all}"
    return msg_content


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    await bot.change_presence(activity=discord.Game(name="Hello There"))


# --------- TEXT MODELS ---------
@bot.event
async def on_message(message):
    if bot.user in message.mentions and '@everyone' not in message.content and '@here' not in message.content:
        time = datetime.datetime.now().time().strftime("%H:%M:%S")
        print(time, message.author.id, message.author, "Message")
        try:
            async with message.channel.typing():
                await message.add_reaction("🕥")
                msg_content = await meta(message, bot)
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{PROXY_URL}/ask", headers={"Content-Type":"application/json"}, json={"messages":[{"role":"user","content":f"{msg_content}"}],"model":"gpt-4-turbo-preview"}) as response:
                    	response = await response.json()
                    	if ["@everyone", "@here"] in response["response"]:
                    		response["response"].replace(["@everyone", "@here"], f" ``` {a} ``` ")
                await message.reply(response["response"])
                await message.remove_reaction("🕥", bot.user)
                await message.add_reaction("😸")
        except Exception as error:
            await message.reply(f"An error occurred: {error}.")
            traceback.print_exc()

bot.run(bot_token)