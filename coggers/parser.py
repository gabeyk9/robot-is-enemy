import json
import re

from discord.ext import commands
from attrs import define

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ROBOT import Bot
else:
    class Scene: pass
    class Bot: pass

@define
class Variant:
    """A single variant."""

    """The variant's name."""
    name: str

    """The variant's arguments."""
    arguments: list

    @classmethod
    def from_string(cls, var):
        name, *arguments = var.split("/")
        return cls(name, arguments)


@define
class Tile:
    """Holds the data for a tile on the grid."""

    """The tile's name."""
    name: str

    """The tile's X position."""
    x: int

    """The tile's Y position."""
    y: int

    """The tile's Z position."""
    z: int

    """The tile's timestamp."""
    t: int

    """Any variants the tile has."""
    # TODO: Variant parsing
    variants: list[Variant]


@define
class Scene:
    """A render scene."""

    """The width of the scene."""
    width: int

    """The height of the scene."""
    height: int

    """The depth of the scene."""
    depth: int

    """The length of the scene."""
    length: int

    """A sparse tile grid."""
    tiles: list[Tile]


# noinspection PyMethodMayBeStatic
class ParserCog(commands.Cog):
    """Cog for handling parsing scenes."""

    def parse(self, string) -> Scene:
        """Parses a string into a scene."""
        # TODO: Flags (should be handled before grid splitting)

        # Split string into lines, then cells, then stack, then time
        rows = string.split("\n")
        parsed_tiles = []
        time, depth, height, width = 0, 0, 0, 0
        for y, row in enumerate(rows):
            stacks = row.split(" ")
            for x, stack in enumerate(stacks):
                steps = re.split(r"(?!\\\\)&", stack)
                for z, step in enumerate(steps):
                    tiles = step.split(">")
                    for t, tile in enumerate(tiles):
                        time = max(time, t)
                        depth = max(depth, z)
                        height = max(height, y)
                        width = max(width, x)
                        tile = re.sub(r"\\(.)", r"\1", tile)
                        name, *variants = tile.split(":")
                        variants = [
                            Variant.from_string(var) for var in variants
                        ]
                        parsed_tiles.append(Tile(
                            name,
                            x, y, z, t,
                            variants
                        ))

        return Scene(
            width,
            height,
            depth,
            time,
            parsed_tiles
        )


async def setup(bot: Bot):
    cog = ParserCog(bot)
    bot.parser = cog
