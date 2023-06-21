import ffmpeg
import time
import os

dir_in = input("File input directory: ")
dir_out = input("File output dir: ")
file_type = input("Image type to convert to (png, jpg, etc): ")
res = input("X and Y res, separate with \"x\" (leave blank for original res): ")
in_list = os.listdir(dir_in)
file = 0

while file < len(in_list):
    try:
        if "mp4" or "mov" or "gif" in in_list[file]:
            os.mkdir(f"{dir_in}/{in_list[file]}split")
            split_out = f"{dir_in}/{in_list[file]}split"
            (
            ffmpeg
            .input(f"{dir_in}/{in_list[file]}")
            .filter('scale', res)
            .output(f"{split_out}/{in_list[file]}.{file_type}")
            .run()
            )
            
        else:
            (
                ffmpeg
                .input(f"{dir_in}/{in_list[file]}")
                .filter('scale', res)
                .output(f"{dir_out}/{in_list[file]}.{file_type}")
                .run()
            )
            
    except:
        print(f"Couldn't convert image {in_list[file]}")
        time.sleep(2)
        
    file += 1