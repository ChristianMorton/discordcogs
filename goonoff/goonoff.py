import asyncio
import random
import discord
from discord.ext import commands
from redbot.core import Config, bank, commands, checks
from redbot.core.utils import AsyncIter
from typing import Literal

class FancyDict(dict):
    def __missing__(self, key):
        value = self[key] = type(self)()
        return value


class FancyDictList(dict):
    def __missing__(self, key):
        value = self[key] = []
        return value

class GoonOff(commands.Cog):
    def __init__(self, bot):
        self.config = Config.get_conf(self, 45465465488435321554234, force_registration=True)
        self.players = FancyDictList()
        self.active = FancyDict()
        self.bot = bot

        guild_defaults = {
            "Wait": 20,
            "Strokes": 6,
        }
        
        member_defaults = {"Wins": 0, "Losses": 0, "Total_Winnings": 0 }

        self.config.register_guild(**guild_defaults)
        self.config.register_member(**member_defaults)
    
        
    async def red_delete_data_for_user(self, *, requester: Literal["discord", "owner", "user", "user_strict"], user_id: int):
        all_members = await self.config.all_members()
        async for guild_id, guild_data in AsyncIter(all_members.items(), steps=100):
            if user_id in guild_data:
                await self.config.member_from_ids(guild_id, user_id).clear()

    @commands.group()
    @commands.guild_only()
    async def goonoff(self, ctx):
        pass
    @goonoff.command()
    async def challenge(self, ctx, opponent: discord.Member):
        """
        Goon with your friends! Remember no cumming allowed!
        """
        wait = await self.config.guild(ctx.guild).Wait()
        chambers = await self.config.guild(ctx.guild).Chambers()
        if self.active[ctx.guild.id]:
            await ctx.send(f"There are already two degenerates gooning off in here, don’t you think that’s enough? Go wait in the corner until the current goons have finished.")
            return 
        if opponent == ctx.author:
            await ctx.send("There’s no challenging yourself to play with yourself against yourself, that’s just masturbation.")
            return
        else: 
            self.players[ctx.guild.id].append(ctx.author)
            await ctx.send(f"{ctx.author.mention} has challenged {opponent.mention} to a goon off! Type ‘yes’ or ‘no’ to accept or reject the challenge")

        def check(msg):
            print(msg.content)
            return msg.author == opponent and msg.content.lower() in ['yes', 'no']

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=wait)
        except asyncio.TimeoutError:
            await ctx.send(f"{opponent.mention} didn't respond in time, probably because they’re already gooning. There will be no goon off.")
            return

        if msg.content.lower() == 'no':
            await ctx.send(f"{opponent.mention} declined the goon. Looks like you’re on your own, {current_player}.")
            return

        # Both players accepted, set the session to active and add the opponent to players
    
        self.active[ctx.guild.id] = True
        self.players[ctx.guild.id].append(opponent)
        
        #This is for logging purposes
        print(self.players)
        print(self.players[ctx.guild.id][0])

        current_player = self.players[ctx.guild.id][random.randint(0, 1)]
        await ctx.send(f"{current_player} edges first.")

        # Set up the game with a bullet in one of the chambers
        maxchambers = await self.config.guild(ctx.guild).Chambers()
        chambers = [0] * maxchambers
        chambers[random.randint(0, maxchambers)] = 1

        # Play the game until someone loses
        while True:
        # Ask the player to pull the trigger
            await ctx.send(f"{current_player.mention}, Uh oh, you can feel it building! Type ‘edge’ to try and hold off…")

            def check(msg):
                print(msg.content)
                return msg.author == current_player and msg.content.lower() in ['edge']

            try:
                msg = await self.bot.wait_for('message', check=check, timeout=wait)
            except asyncio.TimeoutError:
                await ctx.send(f"{current_player.mention} stopped responding. The goon off is cancelled.")
                return
            
            if msg.content.lower() == 'edge':
                await ctx.send(f"{current_player.mention} edges...")
            if chambers.pop(0) == 1:
                winner = self.players[ctx.guild.id][1] if current_player == self.players[ctx.guild.id][0] else self.players[ctx.guild.id][0]
                await ctx.send(f"{current_player.mention} tried to hold back, but they busted all over themselves. What a mess! {winner.mention} wins!")
                addwin = await self.config.user(winner).Wins.set()
                addwin += 1
                addloss = await self.config.user(current_player).Losses.set()
                addloss += 1
                self.active[ctx.guild.id] = False
                break
            else:
                # Switch to the next player
                current_player = self.players[ctx.guild.id][1] if current_player == self.players[ctx.guild.id][0] else self.players[ctx.guild.id][0]