import math
from typing import TYPE_CHECKING
from unittest.util import sorted_list_difference

import cv2
import numpy as np
from PIL import Image
from discord.ext import commands

from classes import Tile, CustomError
import constants

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

DIRECTION_VALUES = {
    "d":0,
    "r":1,
    "u":2,
    "l":3
}

INACTIVE_COLOR = (200, 200, 200, 255)
BLACK_COLOR = (8,8,8,255)
WHITE_COLOR = (255,255,255,255)


# noinspection PyMethodMayBeStatic
class VariantCog(commands.Cog):
    """Cog for handling tile variants."""

    bot: Bot

    palette = np.array(Image.open("data/palette.png"), dtype=np.uint8)
    plate = Image.open("data/custom/sprites/plate_1.png")

    def handle_tile_variants(self, tile: Tile) -> Tile:
        """Handle all tile variants, removing them from the list."""
        new_variants = []
        for variant in tile.running_variants:
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
            elif variant.name == "unit":
                if tile.data.unit:
                    tile.data.unit = False
                else:
                    tile.data.unit = True
            elif variant.name in ("u", "l", "d", "r"):
                dir_value = DIRECTION_VALUES[variant.name]
                tile.direction = dir_value
            else:
                new_variants.append(variant)
        tile.running_variants = new_variants
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
        
        for variant in tile.running_variants:
            print(variant)
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
                arr = np.pad(arr, ((level,level), (level,level), (0,0)))
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
                image = Image.fromarray(base)
            elif variant.name in ("clean", "cl"):
                sort_colors()
                r_max = 0
                g_max = 0
                b_max = 0
                for color in sorted_colors:
                    if color[0] > r_max:
                        r_max = color[0]
                    if color[1] > g_max:
                        g_max = color[1]
                    if color[2] > b_max:
                        b_max = color[2]
                arr = np.array(image, dtype=np.uint8)
                max_color = (r_max/255, g_max/255, b_max/255, 1)
                arr = np.divide(arr, max_color, casting = "unsafe")
                arr = np.array(arr, dtype=np.uint8)
                image = Image.fromarray(arr)
            elif variant.name in ("color", "c"):
                if len(variant.arguments) != 1:
                    if len(variant.arguments) == 2:
                        raise CustomError("You need 1 argument, the color. If you put in 2, you're probably getting confused with RiC.")
                    raise CustomError("You need 1 argument, the color. There's nothing else special here.")
                arr = np.array(image, dtype=np.uint8)
                value = variant.arguments[0]
                if value.startswith("#"):
                    color_string = value[1:]
                    color_int = int(color_string, base=16)
                    color = ((color_int & 0xFF0000) >> 16, (color_int & 0xFF00) >> 8, color_int & 0xFF, 0xFF)
                elif value[1] == ",":
                    try:
                        color_x = int(value[0])
                        color_y = int(value[2])
                    except:
                        raise CustomError("The x and y of the color have to be integers!")
                    try:
                        color = self.palette[color_y, color_x]
                    except:
                        raise CustomError("Palette index out of bounds.")
                elif value in constants.COLOR_NAMES:
                    color_x,color_y = constants.COLOR_NAMES[value]
                    color = self.palette[color_y, color_x]
                arr = np.multiply(arr, np.array(color) / 255, casting="unsafe").astype(np.uint8)
                image = Image.fromarray(arr)
            elif variant.name in ("inactive", "in"):
                arr = np.array(image, dtype=np.uint8)
                color = INACTIVE_COLOR
                arr = np.multiply(arr, np.array(color) / 255, casting="unsafe").astype(np.uint8)
                image = Image.fromarray(arr)
            elif variant.name in ("property", "prop"):
                arr = np.array(image, dtype=np.uint8)
                color = BLACK_COLOR
                arr = np.multiply(arr, np.array(color) / 255, casting="unsafe").astype(np.uint8)
                img_new = Image.fromarray(arr)
                plate = self.plate.copy()
                plate.alpha_composite(img_new)
                image = plate
            elif variant.name in ("noun", "unprop"):
                sort_colors()
                arr = np.array(image, dtype=np.uint8)
                min_color_sum = 765
                min_color = (255,255,255,255)
                for color in sorted_colors:
                    if color[3] > 0:
                        print(color, sum(color[:3]))
                        if sum(color[:3]) < min_color_sum:
                            min_color_sum = sum(color[:3])
                            min_color = color
                arr[arr[...] != min_color] = 255
                arr[arr[..., 0] == 255] = 0
                arr[arr[..., 3] > 0] = 255
                image = Image.fromarray(arr)
            elif variant.name in ("gs", "gscale", "grayscale"):
                arr = np.array(image, dtype=np.uint8)
                arr = arr.astype(np.uint16)
                gray = (arr[..., 0] + arr[..., 1] + arr[..., 2]) // 3 
                arr[..., 0], arr[..., 1], arr[..., 2] = gray, gray, gray
                arr = arr.astype(np.uint8)
                image = Image.fromarray(arr)
            else:
                new_variants.append(variant)
        tile.running_variants = new_variants
        return image


async def setup(bot: Bot):
    cog = VariantCog(bot)
    bot.variant_handler = cog
