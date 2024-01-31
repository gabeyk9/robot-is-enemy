import io
from locale import currency
from pathlib import Path

import cv2
from PIL import Image
import numpy as np
from datetime import datetime
import discord
from discord.ext import commands
from io import BytesIO

import itertools
import math

from typing import TYPE_CHECKING

from coggers.data import TileData, FlagData
from classes import CustomError, Tile

if TYPE_CHECKING:
    from ROBOT import Bot
    from coggers.parser import Scene, Variant
else:
    class Scene:
        pass


    class Bot:
        pass

CUSTOM_WIDTH = {
    2:11,
    3:13,
    4:9
}

CUSTOM_HEIGHT = {
    2:11,
    3:11,
    4:9
}

# noinspection PyMethodMayBeStatic
class RenderCog(commands.Cog):
    sprite_cache: dict[str, Image]
    letter_cache: dict[str, Image]

    def __init__(self, bot: Bot):
        self.bot = bot
        self.sprite_cache = {"-": None, "": None}

    SPACING: int = 12
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

    async def render_scene(self, scene: Scene, flagdata: FlagData) -> list[Image]:
        width = (scene.width + scene.height + 4) * self.SPACING
        height = (scene.height + scene.width + 6 + ((scene.max_depth - scene.min_depth) * 2)) * (self.SPACING // 2)
        bg = Image.new("RGBA", (int(width), int(height)), flagdata.background)
        empty = Image.new("RGBA", (int(width), int(height)), (0, 0, 0, 0))
        final = []

        for wobble in range(3):
            frame = empty.copy()
            background = bg.copy()
            back_array = np.array(background)
            back_array[..., :3][back_array[..., :3] < 0x08] = 0x08
            background = Image.fromarray(back_array)

            for tile in scene.tiles:
                tile: Tile
                
                # Reload the running variants
                tile.running_variants = tile.variants.copy()
                print("----")
                print(tile.running_variants)

                # Add sprites to tile
                sprite = self.get_sprite(tile, wobble)
                if sprite is None:
                    continue
                data = self.bot.data.data.get(tile.name)
                if data is None:
                    data = TileData(directional=False, ground_height=0, frames=1, unit=True, directory="custom_text_")

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

    def get_sprite(self, tile: Tile, wobble: int) -> Image.Image | None:
        name = tile.name
        key = f"{name} {wobble} {tile.direction}"
        if key in self.sprite_cache:
            return self.sprite_cache[key]

        if tile.data.directory == "custom_text_":
            img = self.custom_text(name)
        else:
            data: TileData = self.bot.data.data.get(name)
            if data.frames == 1:
                wobble = 0
            infix = f"_{tile.direction}_" if data.directional else "_"
            path = "sprites/" + name + infix + str(wobble + 1) + ".png"
            try:
                path = Path("data", data.directory, path)
                with Image.open(path) as im:
                    img = im.convert("RGBA").copy()
            except FileNotFoundError:
                raise CustomError(f"Files for `{name}` not found.\nPath: `{path}`")
        self.sprite_cache[key] = img
        return img
    
    def custom_text(self, name):
        word = name.removeprefix("text_")
        lines = []
        word_len = len(word)
        if "/" in word:
            lines = word.split("/")
        else:
            lines = [word]
            if word_len > 3:
                lines = [word[:word_len//2],  word[word_len//2:]]

        if len(lines) == 1:
            line = lines[0]
            letter_mode = 2
            if len(line) > 2:
                letter_mode = 3
        else:
            if len(lines) > 2:
                raise CustomError("You can't make 3 or more line text, since it's too tall.")
            letter_mode = 4
        empty = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
        current_y = CUSTOM_HEIGHT[letter_mode]
        for line in lines:
            path_sizes = []
            for char in line:
                path = f"data/special/letters/{char}"
                print(path)
                char_paths = []

                for char_path in Path(path).glob("*.png"):
                    if char_path.stem.startswith(str(letter_mode)):
                        print("Letter found!")
                        char_paths.append(char_path.stem)
                
                path_size = [int(path_name[-1]) for path_name in char_paths]
                path_sizes.append(path_size.copy())

            # this is a mess
            possible_solutions = itertools.product(*path_sizes)
            current_solutions = []
            solved_length_dist = 100 # there's absolutely no way that the total length is >109
            target_length = CUSTOM_WIDTH[letter_mode]

            print(possible_solutions, path_sizes)

            for solution in possible_solutions:
                for i in [1,2]:
                    print(solved_length_dist)
                    if abs(sum(solution) + i*(len(solution) - 1) - target_length) == solved_length_dist:
                        try:
                            if current_solutions[0][1] == 2 and i == 1:
                                current_solutions = []
                                current_solutions.append((solution, i))
                                solved_length_dist = abs(sum(solution) + i*(len(solution) - 1) - target_length)
                                print("Solutions cleared.")
                        except:
                            pass
                        if not (current_solutions[0][1] == 2 and i == 1):
                            current_solutions.append((solution, i))
                            print("Solution added.")
                    elif abs(sum(solution) + i*(len(solution) - 1) - target_length) < solved_length_dist:
                        current_solutions = []
                        current_solutions.append((solution, i))
                        solved_length_dist = abs(sum(solution) + i*(len(solution) - 1) - target_length)
                        print("Solutions cleared.")
            print(current_solutions)
            active_solution = current_solutions[0] # TODO: implement a better system
            solved_length = sum(active_solution[0]) + active_solution[1]*(len(active_solution[0]) - 1)
            if solved_length > 24:
                raise CustomError("Custom text is too long!")
            current_x = 12 - (solved_length // 2)
            for i in range(len(active_solution[0])):
                char_length = active_solution[0][i]
                char = line[i]
                char_path = f"data/special/letters/{char}/{letter_mode}_{char_length}.png"
                char_img = Image.open(char_path)
                empty.alpha_composite(char_img, (current_x, current_y))
                current_x += char_length + active_solution[1]
            current_y += 6
        return empty

            
    async def render(self, scene: Scene, buffer: BytesIO, flagdata: FlagData):
        """Renders a scene into a buffer."""
        frames: list[Image.Image] = await self.render_scene(scene, flagdata)
        kwargs = {
            'format': "GIF",
            'interlace': True,
            'save_all': True,
            'append_images': frames[1:],
            'loop': 0,
            'duration': 500,
            'optimize': False,
            'disposal': 2
        }
        frames[0].save(
            buffer,
            **kwargs
        )

    @commands.command(name="render", aliases=["r", "t", "tile"])
    async def render_tiles(self, ctx, *, objs: str):
        flagdata = FlagData()
        scene = self.bot.parser.parse(objs, flagdata)
        buf = io.BytesIO()
        await self.render(scene, buf, flagdata)
        buf.seek(0)
        filename = datetime.utcnow().strftime(
            f"render_%Y-%m-%d_%H.%M.%S.gif"  # for now - will gif-ify it later
        )
        # TODO: Command parroting
        await ctx.send(file=discord.File(buf, filename))
async def setup(bot: commands.Bot):
    await bot.add_cog(RenderCog(bot))