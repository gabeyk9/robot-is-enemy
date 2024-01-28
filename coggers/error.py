import os
import traceback

from PIL import Image
import numpy as np
from json import load
from datetime import datetime
import discord
from discord.ext import commands
from io import BytesIO

from classes import CustomError


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error: Exception):
        # This prevents any commands with local handlers being handled here
        # in on_command_error.
        if hasattr(ctx.command, 'on_error'):
            return

        ignored = (
            commands.CommandNotFound,
            commands.NotOwner,
            commands.CheckFailure)

        # Anything in ignored will return and prevent anything happening.
        if isinstance(error, ignored):
            return

        if isinstance(error, commands.errors.CommandInvokeError):
            error: commands.errors.CommandInvokeError
            error: Exception = error.original

        if isinstance(error, commands.CommandOnCooldown):
            if ctx.author.id == self.bot.owner_id:
                return await ctx.reinvoke()
            else:
                return await ctx.reply(str(error))

        if isinstance(error, commands.DisabledCommand):
            await ctx.reply(f'{ctx.command} has been disabled.')

        if isinstance(error, commands.InvalidEndOfQuotedStringError):
            return await ctx.reply(f"Expected a space after a quoted string, got `{error.char}` instead.")

        if isinstance(error, commands.UnexpectedQuoteError):
            return await ctx.reply(f"Got an unexpected quotation mark `{error.quote}` inside a string.")

        if isinstance(error, commands.ConversionError):
            return await ctx.reply("Invalid function arguments provided. Check the help command for the proper format.")

        print(error.__class__, CustomError)
        if error.__class__ is CustomError:
            print("Caught custom error!")
            return await ctx.reply(error.args[0])

        if isinstance(error, ArithmeticError):
            return await ctx.reply(f'Something failed to calculate.\n> {error.args[0]}')

        if isinstance(error, commands.BadArgument):
            return await ctx.reply(f"An invalid argument was provided. Check the help command for the proper format.")

        if isinstance(error, commands.ArgumentParsingError):
            return await ctx.reply("Invalid function arguments provided.")

        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.reply(f"A required argument \"{error.param}\" is missing.")

        if isinstance(error, discord.errors.HTTPException):
            if error.status == 400:
                return await ctx.reply(f"This action could not be performed.\n`{error}`")
            if error.status == 429:
                return await ctx.reply("I'm being ratelimited, wait a few seconds.")
            if error.status == 401:
                return await ctx.reply("This action cannot be performed.")
            if error.status == 503:
                return await ctx.reply("I can't reach the HTTP server.")
            return await ctx.reply("There was an error while processing this action.")

        traceback.print_exception(error)

        emb = discord.Embed(title="Command Error", color=0xE5533B)
        emb.title = f"{type(error).__name__}: {error}"

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

        return await ctx.reply(embed=emb)


async def setup(bot: commands.Bot):
    await bot.add_cog(CommandErrorHandler(bot))
