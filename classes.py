import math

from PIL.Image import Image
from attr import define

from coggers.data import TileData


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
    
    def copy(self):
        new_variant = Variant(self.name, self.arguments)
        return new_variant


@define
class Tile:
    """Holds the data for a tile on the grid."""

    """The tile's name."""
    name: str

    """The tile's X position."""
    x: float

    """The tile's Y position."""
    y: float

    """The tile's Z position."""
    z: float

    """The tile's pixel layer."""
    p: float

    """Any variants the tile has."""
    variants: list[Variant]

    """The currently unhandled variants."""
    running_variants: list[Variant]

    """This tile's data."""
    data: TileData

    """The tile's direction. Goes from 0 to 3."""
    direction: int = 0

    def __lt__(self, other):
        """Returns whether this tile should be drawn under the other tile."""
        if (self.y - self.x) != (other.y - other.x):
            return (self.y - self.x) < (other.y - other.x)
        if self.z != other.z:
            return self.z < other.z
        return self.p < other.p


@define
class Scene:
    """A render scene."""

    """The width of the scene."""
    width: float

    """The height of the scene."""
    height: float

    """The minimum depth of the scene."""
    min_depth: float

    """The maximum depth of the scene."""
    max_depth: float

    """The pixel depth of the scene."""
    pixel_depth: float

    """A sparse tile grid."""
    tiles: list[Tile]

class CustomError(Exception):
    pass