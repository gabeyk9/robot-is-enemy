from PIL import Image
import numpy as np
from json import load
from datetime import datetime
import discord
from discord.ext import commands
from io import BytesIO

class CommandErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error: Exception):
        return await ctx.send(error.args[0])
    
async def setup(bot: commands.Bot):
    await bot.add_cog(CommandErrorHandler(bot))
