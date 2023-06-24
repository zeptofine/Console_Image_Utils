# Console_Image_Utils

## A set of utilities to help with managing images

It was mostly just an excuse to learn bash, and eventually some turned to python.
(Remember to `pip install -r requirements.txt` for the Python scripts to work.)

[Difference.py](Difference.py): Used to convert images from one format to another, and downscale if above a certain threshold.<br>
> `python Difference.py Input/Directory Output/Directory --file-type png --scale 1024`

[Prefix_CopyAll.py](Prefix_CopyAll.py): Used to copy certain images from one folder to another based on a prefix.
> `python Prefix_CopyAll.py Input/Directory Prefix`

[Prefix.DelAll.sh](Prefix.DelAll.sh): Same as CopyAll but for deletions.

[imgbrd_grabber_gen.py](imgbrd_grabber_gen.py): Makes a download list that can be read by <a href="https://github.com/Bionus/imgbrd-grabber">imgbrd-grabber</a>.

[useful_aliases.sh](useful_aliases.sh): A small collection of aliases I find useful.

## Special Scripts

- [special/flip_ui.sh](special/flip_ui.sh) : Switches between TTY and GUI

- [special/logic.py](special/logic.py) : Simplifies truth tables using [logicmin](https://github.com/dreylago/logicmin)

- [special/MountRam.sh](special/MountRam.sh) : Makes a temporary ramdisk

- [special/val_timelapse.sh](special/val_timelapse.sh) : Goes through folder and makes a blended timelapse with the images using `ffmpeg`
