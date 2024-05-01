import aiohttp
import discord
from discord import option
import json
from dotenv import load_dotenv
import os
import traceback
from datetime import datetime, timedelta
import validators
import urllib.parse
import io

load_dotenv()

version = "v1"

# --------- TOKENS ---------
bot_token = os.environ['BOT_KEY']
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
PROXY_URL_CHAT = os.getenv('PROXY_URL_CHAT')
PROXY_URL_IMAGE = os.getenv('PROXY_URL_IMAGE')


user_history = {}
bot = discord.Bot(intents=discord.Intents.default())
system_prompt = "You are a discord bot named AssistMatrix. You can generate images when a user uses the ```/imagine``` command, otherwise you will just respond normally when pinged. You are based on GPT-4-Turbo for text generation, and Dalle-3 for image generation. If a user asks you to generate an image, remind them to use the ```/imagine``` command. If you recive a ```/imagine``` command, remind the user to use the commands built into discord."
intro_message = 'Introduce yourself as AssistMatrix, a discord bot. Do not make stuff up about your capabillites as a discord bot. You are able to respond to messages after being pinged, or generate images with the ```/imagine``` command.'
last_command_time = {"chat":{}, "imagine":{}}


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
        msg_content = intro_message
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
    user_id = str(message.author.id)
    if bot.user in message.mentions and '@everyone' not in message.content and '@here' not in message.content:
        time = datetime.now().time().strftime("%H:%M:%S")
        print(time, user_id, message.author, "Message")
        if user_id in last_command_time["chat"]:
            time_difference = datetime.now() - last_command_time["chat"][user_id]
            if time_difference < timedelta(minutes=2):
                await message.reply(f"Please wait a minute between each message.")
                await message.remove_reaction("🕥", bot.user)
                await message.add_reaction("⛔")
                return
        last_command_time["chat"][user_id] = datetime.now()
        try:
            async with message.channel.typing():
                await message.add_reaction("🕥")
                msg_content = await meta(message, bot)
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{PROXY_URL_CHAT}/ask", headers={"Content-Type":"application/json"}, json={"messages":[{"role":"system","content":system_prompt}, {"role":"user","content":f"{msg_content}"}],"model":"gpt-4-turbo-preview"}) as response:
                        response = await response.json()
                        for substring in ["@everyone", "@here"]:
                            response["response"] = response["response"].replace(substring, f" ``` {substring} ``` ")
                await message.reply(response["response"])
                await message.remove_reaction("🕥", bot.user)
                await message.add_reaction("😸")
        except Exception as error:
            await message.reply(f"An error occurred: {error}.")
            traceback.print_exc()
            await message.remove_reaction("🕥", bot.user)
            await message.add_reaction("⚠")

# --------- IMAGINE---------
@bot.slash_command(description="Generate images")
@option(name="prompt", required=True, description="Prompt to generate")
async def imagine(
    ctx: discord.ApplicationContext,
    prompt: str,
):
    user_id = str(ctx.user.id)
    time = datetime.now().time().strftime("%H:%M:%S")
    print(time, user_id, ctx.user, "Image")
    if user_id in last_command_time["imagine"]:
        time_difference = datetime.now() - last_command_time["imagine"][user_id]
        if time_difference < timedelta(minutes=2):
            await ctx.respond(f"Please wait for 2 minutes between each use of the 'imagine' command.", ephemeral=True)
            return
    last_command_time["imagine"][user_id] = datetime.now()
    try:
        await ctx.respond(f"Generating:\n> {prompt}", ephemeral=True)
        encoded_prompt = urllib.parse.quote(prompt)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{PROXY_URL_IMAGE}/generate?prompt={encoded_prompt}", headers={"Content-Type":"application/json"}) as response:
                content_type = response.headers.get('Content-Type', '')
                if 'image' in content_type:
                    data = await response.read()
                    image_bytes = io.BytesIO(data)
                else:
                    ctx.respond(output["response"], ephemeral=True)
        final = discord.File(image_bytes, 'image.png')
        for substring in ["@everyone", "@here"]:
            prompt = prompt.replace(substring, f" ``` {substring} ``` ")
        await ctx.respond(f"{ctx.user.mention} requested an image:\n**{prompt}**", file=final)
    except Exception as error:
        await ctx.respond(f"An error occurred: {error}.", ephemeral=True)
        traceback.print_exc()
bot.run(bot_token)