#!/bin/bash

SOURCE_DIR="/home/fedora/audiodata_flac"
TARGET_DIR="/home/fedora/audiodata_mp3"

echo "FLAC/WAV files will be read from '$SOURCE_DIR' and MP3 files will be written to '$TARGET_DIR'!"
read -p "Are you sure? (y/N)" -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]] ; then # Continue if user enters "y"

    # Find all flac/wav files in the given SOURCE_DIR and iterate over them:
    find "${SOURCE_DIR}" -type f \( -iname "*.flac" -or -iname "*.wav" \) -print0 | while IFS= read -r -d '' flacFile; do
        if [[ "$(basename "${flacFile}")" != ._* ]] ; then # Skip files starting with "._"
            tmpVar="${flacFile%.*}.mp3"
            mp3File="${tmpVar/$SOURCE_DIR/$TARGET_DIR}"
            mp3FilePath=$(dirname "${mp3File}")
            mkdir -p "${mp3FilePath}"
            if [ ! -f "$mp3File" ]; then # If the mp3 file doesn't exist already
                echo "Input: $flacFile"
                echo "Output: $mp3File"
                ffmpeg -i "$flacFile" -ab 320k -map_metadata 0 -id3v2_version 3 -vsync 2 "$mp3File" < /dev/null
            fi
        fi
    done
fi