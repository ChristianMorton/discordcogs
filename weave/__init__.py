from .weave import Weave


async def setup(bot):
    n = Weave(bot)
    await bot.add_cog(n)
