import io

from PIL import Image
import numpy as np
from datetime import datetime
import discord
from discord.ext import commands
from io import BytesIO

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ROBOT import Bot
    from coggers.parser import Scene
else:
    class Scene: pass
    class Bot: pass


# noinspection PyMethodMayBeStatic
class RenderCog(commands.Cog):
    sprite_cache: dict[str, Image]

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sprite_cache = {"-": None, "": None}

    X_PADDING: int = 2
    X_MULTIPLIER: int = 12
    Y_PADDING: int = 7
    Y_MULTIPLIER: int = 6

    SPACING: int = 12
    STACK_SIZE: int = 8

    def recolor(self, sprite: Image.Image | np.ndarray, rgba: tuple[int, int, int, int]) -> Image.Image | np.ndarray:
        """Apply rgba color multiplication. (0-255)"""
        arr = np.multiply(sprite, np.array(rgba) / 255, casting="unsafe").astype(np.uint8)
        if isinstance(sprite, np.ndarray):
            return arr
        return Image.fromarray(arr)

    async def render_scene(self, scene: Scene) -> list[Image]:
        dummy = Image.new(
            "RGBA",
            (
                (scene.width + scene.height + self.X_PADDING) * self.X_MULTIPLIER,
                (scene.width + scene.height + self.Y_PADDING) * self.Y_MULTIPLIER
            ),
            (0x40, 0x44, 0x64, 255)
        )
        final = []

        for wobble in range(3):
            frame = dummy.copy()
            for tile in scene.tiles:
                # Add sprites to tile
                sprite = self.get_sprite(tile.name, wobble)
                if sprite is None:
                    continue
                data = self.bot.data.data[tile.name]

                # TODO: If there's any image effect variants in the future,
                #       here would be where they'd be applied.

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


                # (x+y+2)*12 - spa.shape[1]//2, (y-x+w+2)*6 - spa.shape[0]//2 + gh*3
                # Adjust coordinates for 3D isometric view
                x_pos = (tile.x + tile.y + 2) * self.SPACING - sprite.width // 2
                y_pos = (tile.y - tile.x + scene.width + 2) * (self.SPACING // 2) \
                    - sprite.height // 2 + data.ground_height * 3 \
                    - tile.z * self.STACK_SIZE
                print(x_pos, y_pos)
                frame.alpha_composite(sprite, (x_pos, y_pos))

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
            frame = frame.resize((frame.width * 2, frame.height * 2), Image.Resampling.NEAREST)
            final.append(frame)

        return final

    def get_sprite(self, tile: str, wobble: int) -> Image.Image | None:
        if tile.startswith("$"):
            tile = "text_" + tile.removeprefix("$")

        key = f"{tile} {wobble}"
        if key in self.sprite_cache:
            return self.sprite_cache[key]

        if tile in ["-", ""]:  # Empty
            return None
        else:
            data = self.bot.data.data.get(tile)
            assert data is not None, f"Tile {tile} does not exist."
            if data.frames == 1:
                wobble = 0
            infix = "_0_" if data.directional else "_"
            path = "data/sprites/" + tile + infix + str(wobble + 1) + ".png"
            try:
                with Image.open(path) as im:
                    img = im.convert("RGBA").copy()
            except FileNotFoundError:
                raise AssertionError(f"Files for `{tile}` not found.\nPath: `{path}`")
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

    @commands.command(name="render", aliases=["r"])
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
