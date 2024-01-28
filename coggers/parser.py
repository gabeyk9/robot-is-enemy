import json
import math
import re
from functools import total_ordering

from discord.ext import commands
from attrs import define

from typing import TYPE_CHECKING
from classes import Tile, Scene, Variant, CustomError
from coggers.data import TileData

if TYPE_CHECKING:
    from ROBOT import Bot
else:
    class Bot:
        pass


# noinspection PyMethodMayBeStatic
class ParserCog(commands.Cog):
    """Cog for handling parsing scenes."""

    def __init__(self, bot: Bot):
        self.bot = bot

    def parse(self, string: str) -> Scene:
        """Parses a string into a scene."""
        # Parse flags
        matches = [match for match in re.finditer(r"--?([^=\s]+)(?:=(\S+))?\s+", string)]
        matches.reverse()  # so that removing a match doesn't mess up other matches
        flags = {}
        for match in matches:
            # Remove the flag
            string = string[:match.start()] + string[match.end():]
            key, value = match.groups()
            flags[key] = value
        ground = flags["ground"] if "ground" in flags else "terrain_0"
        # Split string into lines, then cells, then stack, then time
        rows = string.split("\n")
        parsed_tiles = []
        dims = (0.0, 0.0, (0.0, 0.0), 0.0)
        for y, row in enumerate(rows):
            stacks = row.split(" ")
            for x, stack in enumerate(stacks):
                maybe_terrain = stack.split("%", 1)
                if len(maybe_terrain) == 2:
                    stack = maybe_terrain[1]
                    terrain = maybe_terrain[0]
                else:
                    stack = maybe_terrain[0]
                    terrain = ground
                steps = re.split(r"(?!\\\\)&", stack)

                offset = 0
                for z, step in enumerate(steps):
                    tiles = step.split("|")
                    for p, tile in enumerate(tiles):
                        parsed, dims, this_offset = self.parse_cell((x, y, z, p), tile, dims)
                        offset = max(this_offset, offset)
                        parsed_tiles.append(parsed)

                # Handle terrain
                terrain_parts = terrain.split("|")
                for p, floor in enumerate(terrain_parts):
                    parsed, dims, _ = self.parse_cell((x, y, -1 - (offset / 4), p), floor, dims)
                    parsed_tiles.append(parsed)

        # Sort tiles
        parsed_tiles.sort()

        return Scene(
            dims[0],
            dims[1],
            dims[2][0],
            dims[2][1],
            dims[3],
            parsed_tiles
        )

    def parse_cell(
            self,
            position: tuple[float, float, float, float],
            name: str,
            dimensions: tuple[float, float, tuple[float, float], float]
    ) -> tuple[Tile, tuple[float, float, tuple[float, float], float], int] | None:
        """Parses a single cell."""
        width = max(dimensions[0], position[0])
        height = max(dimensions[1], position[1])
        max_depth = max(dimensions[2][1], position[2])
        min_depth = min(dimensions[2][0], position[2])
        pixel_depth = max(dimensions[3], position[3])
        dimensions = (width, height, (min_depth, max_depth), pixel_depth)

        name = re.sub(r"\\(.)", r"\1", name)
        name, *variants = name.split(":")
        name: str
        if name in [".", ""]:  # Empty
            return None
        if name.startswith("$"):
            name = "text_" + name.removeprefix("$")
        if name.startswith("#"):
            name = "terrain_" + name.removeprefix("#")
        data = self.bot.data.data.get(name)
        if data is None:
            raise CustomError(f"There's no tile called `{name}`.")
        else:
            offset = data.ground_height
        variants = [
            Variant.from_string(var) for var in variants
        ]
        # noinspection PyTypeChecker
        # false alarm
        tile = Tile(
            name,
            *position,
            variants,
            data
        )
        tile = self.bot.variant_handler.handle_tile_variants(tile)
        return tile, dimensions, offset


async def setup(bot: Bot):
    cog = ParserCog(bot)
    bot.parser = cog
