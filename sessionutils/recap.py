import asyncio
from redbot.core import commands, checks
from datetime import datetime, timedelta
import json
from typing import List
import os
from .recap_ai.recap_ai import OpenAI
import glob
import discord


openai = OpenAI()
openai.api_key = os.getenv("OPENAI_API_KEY")


class Recap(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.enabled = False  # Still to add global enable/disable command
        self.timer = 5  # Placeholder for timer
        self.temp_messages = []
        self.collecting = False

    def read_recap(self):
        with open(".\\recap.json", "r") as file:
            data = json.load(file)
            return data["recap"]

    def update_recap(self, data_to_update):
        with open(".\\recap.json", "w") as file:
            json.dump(data_to_update, file)

    def get_latest_recap(self):
        return max(glob.glob("recap_*.txt"), key=os.path.getctime)

    @commands.group()
    @checks.admin_or_permissions(manage_messages=True)
    async def recap(self, ctx):
        """Record a log of the DND session and recap the story so far with."""
        pass

    @recap.command()
    async def start(self, ctx):
        """Start collecting messages for recap."""
        self.collecting = True
        await ctx.send("Started collecting messages for the recap.")

    @recap.command()
    async def stop(self, ctx):
        """Stop collecting messages."""
        self.collecting = False
        collected_text = " ".join(self.temp_messages)
        file_name = f"recap_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        with open(file_name, "w") as file:
            file.write(collected_text)
        await ctx.send(f"Stopped collecting messages. Recap saved to {file_name}.")
        self.temp_messages = []

    @recap.command()
    async def generate(self, ctx):
        """Send the latest recap to OpenAI for story generation."""
        await ctx.send("Generating recap...")
        file_name = self.get_latest_recap()
        with open(file_name, "r") as file:
            prompt = file.read()
            response = openai.recap_to_story_gpt4(prompt)
            await ctx.send(response)

    @recap.command()
    async def announce(self, ctx, message: str):
        """Announce to the Town Crier"""
        await ctx.send(message)
        # send the message in the town crier channel
        target_channel = self.bot.get_channel(1154282874401456149)
        if target_channel is None:
            await ctx.send("Channel not found")
            return
        header = "__**DND Session Recap__"
        full_message = f"{header}\n{message}"
        await target_channel.send(full_message)
        await ctx.send("Announcement posted to Town Crier")

    @recap.command()
    async def help(self, ctx):
        """Recap Help Menu"""
        # make an embed
        embed = discord.Embed(
            title="Recap Help Menu", description="Recap Help Menu", color=0xEEE657
        )

        # set the fields of the embed
        embed.add_field(
            name="!recap start",
            value="Start collecting messages for the recap",
            inline=False,
        )
        embed.add_field(
            name="!recap stop",
            value="Stop collecting messages for the recap",
            inline=False,
        )
        embed.add_field(
            name="!recap generate",
            value="Send the latest recap to OpenAI for story generation",
            inline=False,
        )
        embed.add_field(
            name="!recap announce",
            value="Announce the latest recap to the Town Crier",
            inline=False,
        )

        await ctx.send(embed=embed)

    @commands.Cog.listener("on_message")
    async def on_message_listener(self, message):
        if message.author.bot:
            return

        if self.collecting:
            self.temp_messages.append(message.content)


def setup(bot):
    bot.add_cog(Recap(bot))
