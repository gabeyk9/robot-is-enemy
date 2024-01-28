import io
from pathlib import Path

import cv2
from PIL import Image
import numpy as np
from datetime import datetime
import discord
from discord.ext import commands
from io import BytesIO

from typing import TYPE_CHECKING

from coggers.data import TileData
from classes import CustomError, Tile

if TYPE_CHECKING:
    from ROBOT import Bot
    from coggers.parser import Scene, Variant
else:
    class Scene:
        pass


    class Bot:
        pass


# noinspection PyMethodMayBeStatic
class RenderCog(commands.Cog):
    sprite_cache: dict[str, Image]

    def __init__(self, bot: Bot):
        self.bot = bot
        self.sprite_cache = {"-": None, "": None}

    SPACING: int = 12
    BACKGROUND_COLOR: tuple[int, int, int, int] = (0x40, 0x44, 0x64, 0xFF)
    UNIT_KERNEL: np.ndarray = np.array([
        [0,  1, 0],
        [1, -6, 1],
        [1,  1, 1]
    ])

    def recolor(self, sprite: Image.Image | np.ndarray, rgba: tuple[int, int, int, int]) -> Image.Image | np.ndarray:
        """Apply rgba color multiplication. (0-255)"""
        arr = np.multiply(sprite, np.array(rgba) / 255, casting="unsafe").astype(np.uint8)
        if isinstance(sprite, np.ndarray):
            return arr
        return Image.fromarray(arr)

    async def render_scene(self, scene: Scene) -> list[Image]:
        width = (scene.width + scene.height + 4) * self.SPACING
        height = (scene.height + scene.width + 6 + ((scene.max_depth - scene.min_depth) * 2)) * (self.SPACING // 2)
        bg = Image.new("RGBA", (int(width), int(height)), self.BACKGROUND_COLOR)
        empty = Image.new("RGBA", (int(width), int(height)), (0, 0, 0, 0))
        final = []

        for wobble in range(3):
            frame = empty.copy()
            background = bg.copy()
            for tile in scene.tiles:
                tile: Tile
                # Add sprites to tile
                sprite = self.get_sprite(tile.name, wobble)
                if sprite is None:
                    continue
                data = self.bot.data.data.get(tile.name)

                # Handle sprite variants
                sprite = self.bot.variant_handler.handle_sprite_variants(tile, sprite)

                # TODO: Reimplement border
                # sp = row[i]
                # d = drow[i]
                # spa = np.array(sp, dtype=np.uint8)
                # if d["unit"] == "true":
                #     spa = np.pad(spa, ((1, 1), (1, 1), (0, 0)))
                #     ker = np.array([[0, 1, 0],
                #                     [1, -8, 1],
                #                     [1, 1, 1]])
                #     base = spa[..., 3]
                #     base = cv2.filter2D(src=base, ddepth=-1, kernel=ker)
                #     base = np.dstack((base, base, base, base))
                #     mask = spa[..., 3] > 0
                #     base[mask, ...] = 0
                #     base = recolor(base, (8, 8, 8, 255))
                #     spa = layer_ontop(spa, base, 0, 0)
                if tile.data.unit:
                    sprite = np.array(sprite)
                    sprite = np.pad(sprite, ((1, 1), (1, 1), (0, 0)))
                    base = sprite[..., 3]
                    base = cv2.filter2D(src=base, ddepth=-1, kernel=self.UNIT_KERNEL)
                    base = np.dstack((base, base, base, base))
                    mask = sprite[..., 3] > 0
                    base[mask, ...] = 0
                    base = self.recolor(base, (8, 8, 8, 255))
                    base = Image.fromarray(base)
                    sprite = Image.fromarray(sprite)
                    sprite.alpha_composite(base)
                # Adjust coordinates for 3D isometric view
                x_pos = (tile.x + tile.y + 2) * self.SPACING - sprite.width // 2
                y_pos = (
                        (tile.y - tile.x + scene.width + 3 + scene.max_depth * 2)
                        * (self.SPACING // 2)
                        - sprite.height // 2
                        + data.ground_height * 3
                        - tile.z * self.SPACING
                )
                frame.alpha_composite(sprite, (int(x_pos), int(y_pos)))

                # TODO: Reimplement whatever the fuck this is
                # base = final[..., 3]
                # base = cv2.filter2D(src=base, ddepth=-1, kernel=ker)
                # base = np.dstack((base, base, base, base))
                # mask = final[..., 3] > 0
                # base[mask, ...] = 0
                # base = recolor(base, (8, 8, 8, 255))
                # final = layer_ontop(final, base, 0, 0)
                # end = Image.new("RGBA", ((width + height + 2) * 12, (width + height + 7) * 6), (0x40, 0x44, 0x64))
                # ea = np.array(end, dtype=np.uint8)
                # final = layer_ontop(ea, final, 0, 0)
                # # -m=2 effect
                # dim = final.shape[:2] * np.array((2, 2))
                # dim = dim.astype(int)
                # final = cv2.resize(final[:, ::-1], dim[::-1], interpolation=cv2.INTER_NEAREST)[:, ::-1]

            frame = np.array(frame)
            frame = np.pad(frame, ((1, 1), (1, 1), (0, 0)))
            base = frame[..., 3]
            base = cv2.filter2D(src=base, ddepth=-1, kernel=self.UNIT_KERNEL)
            base = np.dstack((base, base, base, base))
            mask = frame[..., 3] > 0
            base[mask, ...] = 0
            base = self.recolor(base, (8, 8, 8, 255))
            base = Image.fromarray(base)
            frame = Image.fromarray(frame)
            frame.alpha_composite(base)
            background.alpha_composite(frame)
            frame = background

            frame = frame.resize((frame.width * 2, frame.height * 2), Image.Resampling.NEAREST)
            final.append(frame)

        return final

    def get_sprite(self, tile: str, wobble: int) -> Image.Image | None:
        key = f"{tile} {wobble}"
        if key in self.sprite_cache:
            return self.sprite_cache[key]

        data: TileData = self.bot.data.data.get(tile)
        if data.frames == 1:
            wobble = 0
        infix = "_0_" if data.directional else "_"
        path = "sprites/" + tile + infix + str(wobble + 1) + ".png"
        try:
            path = Path("data", data.directory, path)
            with Image.open(path) as im:
                img = im.convert("RGBA").copy()
        except FileNotFoundError:
            raise CustomError(f"Files for `{tile}` not found.\nPath: `{path}`")
        self.sprite_cache[key] = img
        return img

    async def render(self, scene: Scene, buffer: BytesIO):
        """Renders a scene into a buffer."""
        frames: list[Image.Image] = await self.render_scene(scene)
        kwargs = {
            'format': "GIF",
            'interlace': True,
            'save_all': True,
            'append_images': frames[1:],
            'loop': 0,
            'duration': 600,
            'optimize': False,
            'disposal': 2
        }
        frames[0].save(
            buffer,
            **kwargs
        )

    @commands.command(name="render", aliases=["r", "t", "tile"])
    async def render_tiles(self, ctx, *, objs: str):
        scene = self.bot.parser.parse(objs)
        buf = io.BytesIO()
        await self.render(scene, buf)
        buf.seek(0)
        filename = datetime.utcnow().strftime(
            f"render_%Y-%m-%d_%H.%M.%S.gif"  # for now - will gif-ify it later
        )
        # TODO: Command parroting
        await ctx.send(file=discord.File(buf, filename))
async def setup(bot: commands.Bot):
    await bot.add_cog(RenderCog(bot))