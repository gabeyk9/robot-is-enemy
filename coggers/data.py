import json
from pathlib import Path

from discord.ext import commands
from attrs import define

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ROBOT import Bot
else:
    class Scene: pass
    class Bot: pass

@define
class TileData:
    """Holds the data for a singular tile."""

    """Whether or not the tile has directions."""
    directional: bool

    """The vertical offset for ground height"""
    ground_height: int

    """The amount of frames this tile has."""
    frames: int

    """Whether or not this tile is a unit."""
    unit: bool

    """The directory that this tile resides in."""
    directory: str

    def copy(self):
        new_data = TileData(directional=self.directional, ground_height=self.ground_height, frames=self.frames, unit=self.unit, directory=self.directory)
        return new_data
    
@define
class FlagData:
    """The data gotten from the flags."""
    
    """The color of the background."""
    background: tuple[int, int, int, int] = (0x40, 0x44, 0x64, 0xFF)


class DataCog(commands.Cog):
    """Cog for handling loading data."""

    """The cached data for the tiles."""
    data: dict[str, TileData]

    """Loads tile data for all tiles."""

    def load_tile_data(self):
        self.data = {}
        for path in Path("data").glob("*/"):
            if path.name != "special":
                with open(path / "tiles.json") as t:
                    obj: dict[str, dict] = json.load(t)
                for (name, tile) in obj.items():
                    tile_data = TileData(
                        tile["dir"],
                        tile["ground"],
                        tile["frames"],
                        tile["unit"],
                        path.name
                    )
                    self.data[name] = tile_data


async def setup(bot: Bot):
    cog = DataCog(bot)
    cog.load_tile_data()
    bot.data = cog
