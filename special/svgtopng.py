import os
import ffmpeg
import time

dir_in = input("SVG input dir: ")
dir_out = input("PNG output dir: ")
res = input("X and Y res, separate with \"x\" (leave blank for original res): ")
in_list = os.listdir(dir_in)
file = 0

while file < len(in_list):
    try:
        (
            ffmpeg
            .input(f"{dir_in}/{in_list[file]}")
            .filter('scale', res)
            .output(f"{dir_out}/{in_list[file]}.png")
            .run()
        )
    except:
        print(f"Couldn't convert image {in_list[file]}")
        time.sleep(2)
    file += 1