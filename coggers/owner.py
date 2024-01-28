from PIL import Image
import numpy as np
from json import load
from datetime import datetime
import discord
from discord.ext import commands
from io import BytesIO
import asyncio

class OwnerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command(aliases=["rr"])
    async def reload(self, ctx):
        extensions = [a for a in self.bot.extensions.keys()]
        await asyncio.gather(*((self.bot.reload_extension(extension)) for extension in extensions))
        await ctx.send("Reloaded all extensions.")
    
async def setup(bot: commands.Bot):
    await bot.add_cog(OwnerCog(bot))
