import math
from typing import TYPE_CHECKING

import cv2
import numpy as np
from PIL import Image
from discord.ext import commands

from classes import Tile, CustomError

if TYPE_CHECKING:
    from ROBOT import Bot
else:
    class Bot:
        pass

META_LIMIT = 16
META_KERNEL = np.array([
    [0, 1, 0],
    [1, -4, 1],
    [0, 1, 0]
], dtype=np.int32)


# noinspection PyMethodMayBeStatic
class VariantCog(commands.Cog):
    """Cog for handling tile variants."""

    def handle_tile_variants(self, tile: Tile) -> Tile:
        """Handle all tile variants, removing them from the list."""
        new_variants = []
        for variant in tile.variants:
            if variant.name in ("displace", "disp"):
                if len(variant.arguments) != 3:
                    raise CustomError("Need 3 numeric arguments for displacement (one for each axis).")
                x, y, z = variant.arguments
                try:
                    x, y, z = float(x), float(y), float(z)
                except ValueError:
                    raise CustomError("All arguments for displacement need to be numeric!")
                # Don't change this to an assert, it breaks when running under -O
                if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
                    raise CustomError("Do you think I'm dumb or something?")
                tile.x += x
                tile.y += y
                tile.z += z
            else:
                new_variants.append(variant)
        tile.variants = new_variants
        return tile

    def handle_sprite_variants(self, tile: Tile, image: Image.Image) -> Image.Image:
        """Handle all sprite variants, removing them from the list."""
        new_variants = []

        sorted_colors: np.ndarray = None

        # This is done so that we only sort when it's needed,
        # but it's convenient to when it IS needed
        def sort_colors():
            nonlocal sorted_colors
            if sorted_colors is None:
                array = np.array(image)
                colors = array.reshape(-1, 4)
                colors = colors[colors[..., 3] != 0]
                (colors, counts) = np.unique(colors, axis=0, return_counts=True)
                sorted_colors = colors[np.argsort(counts)[::-1]]

        for variant in tile.variants:
            if variant.name in ("meta", "m"):
                sort_colors()
                level = 1
                if len(variant.arguments):
                    try:
                        level = int(variant.arguments[0])
                    except ValueError:
                        raise CustomError("Meta level must be an integer!")
                if level < 1:
                    raise CustomError("Meta level must be positive!")
                if level > META_LIMIT:
                    raise CustomError(f"Meta level can't be greater than {META_LIMIT}!")
                arr = np.array(image, dtype=np.uint8)
                base = arr[..., 3]
                for _ in range(level):
                    base = cv2.filter2D(src=base, ddepth=-1, kernel=META_KERNEL)
                base = np.dstack((base, base, base, base))
                base = base.astype(float) / 255
                base *= sorted_colors[0]
                base = base.astype(np.uint8)
                mask = arr[..., 3] > 0
                if not (level % 2) and level > 0:
                    base[mask, ...] = arr[mask, ...]
                else:
                    base[mask, ...] = 0
                return Image.fromarray(base)
            else:
                new_variants.append(variant)
        tile.variants = new_variants
        return image


async def setup(bot: Bot):
    cog = VariantCog(bot)
    bot.variant_handler = cog
