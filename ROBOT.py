import discord
from discord.ext import commands
import os
import auth
import asyncio

import config

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from coggers.parser import ParserCog
    from coggers.data import DataCog


class Context(commands.Context):  # taken from ric
    silent: bool = False

    async def send(self, content: str = "", embed: discord.Embed | None = None, **kwargs):
        content = str(content)
        if len(content) > 2000:
            msg = " [...] \n\n (Character limit reached!)"
            content = content[:2000 - len(msg)] + msg
        if embed is not None:
            if content:
                return await super().send(content, embed=embed, **kwargs)
            return await super().send(embed=embed, **kwargs)
        elif content:
            return await super().send(content, embed=embed, **kwargs)
        return await super().send(**kwargs)

    async def reply(self, *args, mention_author: bool = False, **kwargs):
        kwargs['mention_author'] = mention_author
        kwargs['reference'] = self.message
        return await self.send(*args, **kwargs)


class Bot(commands.Bot):
    parser: commands.Cog
    data: commands.Cog

    def __init__(self, *args, cogs, **kwargs):
        super().__init__(*args, **kwargs)

        async def gather_cogs():
            await asyncio.gather(*(self.load_extension(cog, package='ROBOT') for cog in cogs))

        asyncio.run(gather_cogs())
        print("Bot is running!")


intents = discord.Intents.default()
intents.message_content = True

bot = Bot(cogs=config.cogs, command_prefix=config.prefix, intents=intents)

bot.run(auth.token, log_handler=None)
