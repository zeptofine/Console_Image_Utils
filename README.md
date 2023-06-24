# Console_Image_Utils

## A set of utilities to help with managing images

It was mostly just an excuse to learn bash, and eventually some turned to python.
(Remember to `pip install -r requirements.txt` for the Python scripts to work.)

### [Difference.py](Difference.py)

<details>
Used to convert images from one format to another, and downscale if above a certain threshold.
`python Difference.py Input/Directory Output/Directory --file-type png --scale 1024`
</details>

### [Prefix_CopyAll.py](Prefix_CopyAll.py)

<details>
Used to copy certain images from one folder to another based on prefix.
`python Prefix_CopyAll.py Input/Directory Output/Directory --prefix Prefix`
</details>

### [Prefix.DelAll.sh](Prefix.DelAll.sh)

<details>
Same as CopyAll but for deletions. (Needs to be translated to Python)
</details>

### [imgbrd_grabber_gen.py](imgbrd_grabber_gen.py)

<details>
Makes a download list that can be read by <a href="https://github.com/Bionus/imgbrd-grabber">imgbrd-grabber</a>.
</details>

### [useful_aliases.sh](useful_aliases.sh)

<details>
A small collection of aliases I find useful.
</details>

## Special Scripts

- [special/flip_ui.sh](special/flip_ui.sh) : Switches between TTY and GUT

- [special/logic.py](special/logic.py) : Simplifies truth tables using logicmin

- [special/MountRam.sh](special/MountRam.sh) : Makes ramdisk

- [special/val_timelapse.sh](special/val_timelapse.sh) : Goes through folder and makes blended timelapse with the images
