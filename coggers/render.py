from PIL import Image
import numpy as np
from json import load
from datetime import datetime
import discord
from discord.ext import commands
from io import BytesIO
import cv2

def layer_ontop(a1, a2, x, y):
    for i in range(a2.shape[0]):
        for j in range(a2.shape[1]):
            if a2[i, j, 3] != 0:
                a1[i+y, j+x] = a2[i, j]
    return a1

def recolor(sprite: Image.Image | np.ndarray, rgba: tuple[int, int, int, int]) -> Image.Image:
    """Apply rgba color multiplication (0-255)""" #ty ric
    arr = np.multiply(sprite, np.array(rgba) / 255, casting="unsafe").astype(np.uint8)
    if isinstance(sprite, np.ndarray):
        return arr
    return Image.fromarray(arr)

class RenderCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def tiledata(self, name):
        ftd = None
        with open("data/tiledata.json") as t:
            j = load(t)
            try:
                ftd = j[name]
            except:
                raise AssertionError(f"The tile `{name}` could not be found.")
        return ftd
    
    async def makeimage(self, sprites, data, w, h):
        final = Image.new("RGBA", ((w+h+2)*12, (w+h+7)*6), (0,0,0,0))
        
        final = np.array(final, dtype=np.uint8)

        #adding ground
        y = 0
        for j in range(len(sprites)):
            row = sprites[j]
            drow = data[j]
            x = len(row) - 1
            for i in range(len(row)):
                terrain = Image.open("data/special/terrain_0_1.png").convert("RGBA")
                ta = np.array(terrain, dtype=np.uint8)
                final = layer_ontop(final, ta, (x+y+1)*12, (y-x+w+2)*6)
                x -= 1
            y += 1

        y = 0
        for j in range(len(sprites)):
            row = sprites[j]
            drow = data[j]
            x = len(row) - 1
            for i in range(len(row)):
                sp = row[i]
                d = drow[i]
                spa = np.array(sp, dtype=np.uint8)
                if d["unit"]:
                    spa = np.pad(spa, ((1, 1), (1, 1), (0, 0)))
                    ker = np.array([[0, 1, 0],
                      [1, -8, 1],
                      [1, 1, 1]])
                    base = spa[..., 3]
                    base = cv2.filter2D(src=base, ddepth=-1, kernel=ker)
                    base = np.dstack((base, base, base, base))
                    mask = spa[..., 3] > 0
                    base[mask, ...] = 0
                    base = recolor(base, (8,8,8,255))
                    spa = layer_ontop(spa, base, 0, 0)
                final = layer_ontop(final, spa, (x+y+2)*12 - spa.shape[1]//2, (y-x+w+2)*6 - spa.shape[0]//2)
                x -= 1
            y += 1

        final = np.pad(final, ((1, 1), (1, 1), (0, 0)))
        ker = np.array([[0, 1, 0],
            [1, -8, 1],
            [1, 1, 1]])
        base = final[..., 3]
        base = cv2.filter2D(src=base, ddepth=-1, kernel=ker)
        base = np.dstack((base, base, base, base))
        mask = final[..., 3] > 0
        base[mask, ...] = 0
        base = recolor(base, (8,8,8,255))
        final = layer_ontop(final, base, 0, 0)

        end = Image.new("RGBA", ((w+h+2)*12, (w+h+7)*6), (0x40, 0x44, 0x64))
        ea = np.array(end, dtype=np.uint8)
        final = layer_ontop(ea, final, 0,0)

        # -m=2 effect
        dim = final.shape[:2] * np.array((2, 2))
        dim = dim.astype(int)
        final = cv2.resize(final[:, ::-1], dim[::-1], interpolation=cv2.INTER_NEAREST)[:, ::-1]

        final = Image.fromarray(final)
        return final
    
    async def getsd(self, tile, wobble):
        if tile[0] == "$":
            try:
                tile = "text_" + tile[1:]
            except:
                pass
        td = {"name":"", "dir":"false", "ground":"0", "frames":"1", "unit":"false"}
        if tile in ["-", ""]:
            img = Image.new("RGBA", (24,24), (0,0,0,0))
        else:
            td = await self.tiledata(tile)
            spname = tile
            if "sprite" in td.keys():
                spname = td["sprite"]
            if td["frames"] == 1:
                wobble = 0
            if td["dir"]:
                path = "data/sprites/" + spname + "_0_" + str(wobble+1) + ".png"
            else:
                path = "data/sprites/" + spname + "_" + str(wobble+1) + ".png"
            try:
                img = Image.open(path).convert("RGBA")
            except:
                raise AssertionError(f"Files for `{tile}` not found. Path: `{path}`")
        return img, td

    async def render(self, ctx, objs):
        desc = f"`{ctx.message.content.split(' ', 1)[0]} {objs}`"
        # splitting
        nobjs = objs.split("\n")
        nnobjs = []
        for obj in nobjs:
            obj = obj.split(" ")
            nnobjs.append(obj[::-1])
        objs = nnobjs

        images = []
        for wobble in range(3):
            sprites = []
            data = []
            for row in objs:
                sprites.append([])
                data.append([])
                for tile in row:
                    img, td = await self.getsd(tile, wobble)
                    sprow = sprites[-1]
                    drow = data[-1]
                    sprow.append(img)
                    drow.append(td)

            #combining
            h = 0
            w = 0
            for row in sprites:
                h += 1
                w = max(w, len(row))

            final = await self.makeimage(sprites, data, w, h)

            images.append(final)

        kwargs = {
                'format': "GIF",
                'interlace': True,
                'save_all': True,
                'append_images': images[1:],
                'loop': 0,
                'duration': [600]*3,
                'optimize': False
            }

        out = BytesIO()
        images[0].save(
                out,
                **kwargs
            )
        filename = datetime.utcnow().strftime(
                    f"render_%Y-%m-%d_%H.%M.%S.gif") #for now- will gif-ify it later
        out.seek(0)
        image = discord.File(out, filename=filename)

        await ctx.send(desc[:2000], file=image)

    @commands.command(name="render", aliases=["r"])
    async def render_tiles(self, ctx, *, objs):
        await self.render(ctx, objs)

async def setup(bot: commands.Bot):
    await bot.add_cog(RenderCog(bot))
