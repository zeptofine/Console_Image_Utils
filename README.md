# Console_Image_Utils

## A set of utilities to help with managing images

~~but mostly just an excuse to learn Python~~

Remember to `pip install -r requirements.txt` for the Python scripts to work!

### Difference.py

<details>
Used to convert images from one format to another, and downscale if above a certain threshold.
`python Difference.py Input/Directory Output/Directory --file-type png --scale 1024`
</details>

### Prefix_CopyAll.py

<details>
Used to copy certain images from one folder to another based on prefix.
`python Prefix_CopyAll.py Input/Directory Output/Directory --prefix Prefix`
</details>

### Prefix.DelAll.sh

Same as CopyAll but for deletions. (Needs to be translated to Python)

### imgbrd_grabber_gen.py

Makes a download list that can be read by <a href="https://github.com/Bionus/imgbrd-grabber">imgbrd-grabber</a>.

#### Special Scripts

<details>
    special/flip_ui.sh : Switches between TTY and GUI <br>
    special/logic.py : Simplifies truth tables using logicmin <br>
    special/MountRam.sh : Makes ramdisk <br>
    special/val_timelapse.sh : Goes through folder and makes blended timelapse with the images
</details>