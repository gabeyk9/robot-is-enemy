import glob
import os
import sys
from pathlib import Path
import shutil


def main():
    args = sys.argv
    if len(args) < 2:
        print("Usage:\n\tsetup.py <path to MSB install>")
        return
    path = Path(args[1]) / 'Data'
    if Path("data").exists():
        shutil.rmtree("data")
    os.mkdir("data")
    os.mkdir("data/sprites")
    os.system(f"lua converter.lua {path / 'values.lua'} data/values.json")
    for file in (path / 'assets' / 'default' / 'sprites').glob('*.png'):
        shutil.copy2(file, "data/sprites/")
    shutil.copytree(path / 'assets' / 'default' / 'sprites' / 'terrain', "data/terrain/")
    print("Done")


if __name__ == "__main__":
    main()
