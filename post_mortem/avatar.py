import discord
import asyncio
from redbot.core import commands


class Avatar:
    def __init__(self, user):
        self.user = user


async def get_avatar(self, ctx, user: discord.Member = None):
    """Sends the avatar of the user mentioned"""
    user = user or ctx.author  # if no user is mentioned, use the command invoker
    await ctx.send(user.avatar_url)
