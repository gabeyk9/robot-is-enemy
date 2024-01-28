from typing import TYPE_CHECKING

from PIL import Image
import numpy as np
from json import load
from datetime import datetime
import discord
from discord.ext import commands
from io import BytesIO
import asyncio

if TYPE_CHECKING:
    from ROBOT import Bot
else:
    class Bot:
        pass


class OwnerCog(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.is_owner()
    @commands.command(aliases=["rr"])
    async def reload(self, ctx):
        await asyncio.gather(*((
            self.bot.reload_extension(extension))
            for extension in self.bot.extensions.keys()
        ))
        await ctx.send("Reloaded all extensions.")


async def setup(bot: Bot):
    await bot.add_cog(OwnerCog(bot))
