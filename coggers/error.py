import os
import traceback

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
        error: Exception = getattr(error, 'original', error)

        emb = discord.Embed(title="Command Error", color=0xE5533B)
        emb.title = f"Error: {error}"

        if os.name == "nt":
            trace = '\n'.join(
                traceback.format_tb(
                    error.__traceback__)
                ).replace(
                    os.getcwd(),
                    os.path.curdir
            ).replace(
                os.environ["USERPROFILE"],
                ""
            )
        else:
            trace = '\n'.join(
                traceback.format_tb(
                    error.__traceback__
                )
            ).replace(
                os.getcwd(),
                os.path.curdir
            )
        if len(trace) > 4000:
            trace = trace[:2000] + '...' + trace[-2000]

        emb.description = f"""```python\n{trace}\n```"""

        return await ctx.send(embed=emb)
    
async def setup(bot: commands.Bot):
    await bot.add_cog(CommandErrorHandler(bot))
