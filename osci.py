import argparse
import subprocess
import tempfile
from itertools import islice
from pathlib import Path
from queue import Queue
from threading import Thread

import cv2
import ffmpeg
import numpy as np
import psutil
from scipy.io.wavfile import read
from tqdm import tqdm


# read `whistle.wav`
def batched(iterable, n):
    "Batch data into tuples of length n. The last batch may be shorter."
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


def window(iterable, n):
    "Sliding window of length n over data from iterable"
    it = iter(iterable)
    window = tuple(islice(it, n))
    if len(window) == n:
        yield window
    for item in it:
        window = window[1:] + (item,)
        yield window


def generate_lines(arr: np.ndarray, samples_per_frame: int, dissipation: float, out_q: Queue):
    canvas = np.zeros((size, size), dtype=float)
    samplecount = 1
    for pts in window(tqdm(arr, unit="sample"), 2):
        cv2.line(canvas, pts[0], pts[1], (1, 1, 1), 1)
        samplecount += 1
        if samplecount >= samples_per_frame:
            out_q.put(canvas.copy())
            canvas *= dissipation
            samplecount = 0
    out_q.put(None)


def get_queue_size(read_size: int, gb_target: int):
    gb_bytes = int(gb_target * (10**9))

    # Example:
    # free memory before: 18.58 GB
    # free memory with predicted given usage: -5.45 GB
    # Chosen memory usage is too large, resizing for a minimum of 1 gb free
    # using 1.58 GB
    # estimaged total usage is less than gb usage. Video will likely fit in less space than specified
    # free with predicted total usage: 12.69 GB

    # get amount of system memory
    virtual_memory = psutil.virtual_memory()

    print(f"free memory before: {virtual_memory.available / (10 ** 9):.2f} GB")
    print(f"free memory with predicted given usage: {(virtual_memory.available - gb_bytes) / (10 ** 9):.2f} GB")
    if virtual_memory.available - gb_bytes < 10**9:
        print("Chosen memory usage is too large, resizing for a minimum of 1 gb free")

        while virtual_memory.available - gb_bytes < 10**9:
            gb_bytes -= 10**9
        print(f"using {gb_bytes // (10 ** 9):.2f} GB")

    # estimate the total number of bytes in the video
    total_usage = read_size * total_frames

    # if the total number of bytes in the video is smaller than the allowed ram threshold
    if total_usage < gb_bytes:
        print("estimaged total usage is less than given usage. Video will likely fit in less space than specified")
        print(f"free memory with predicted total usage: {(virtual_memory.available - total_usage) / (10 ** 9):.2f} GB")

    # calculate how many images can fit in a given amount of memory
    return int(gb_bytes // read_size)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--output", "-o", default="output.mkv")
    parser.add_argument("--fps", "-r", type=int, default=48)
    parser.add_argument("--size", "-s", type=int, default=800)
    parser.add_argument("--dissipation", "-d", type=float, default=0.75)
    parser.add_argument("--preview", action="store_true", default=False)
    parser.add_argument("--gb_usage", type=float, default=2)
    args = parser.parse_args()

    input_file = args.file
    output_file = args.output
    fps = args.fps
    size = args.size
    dissipation = args.dissipation
    preview = args.preview
    gb_usage = args.gb_usage

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        tmpfile = tmpdir / "audio.wav"
        ffmpeg.output(ffmpeg.input(input_file), str(tmpfile)).run(quiet=True)

        samplerate: int  # samples / sec
        samples: np.ndarray  # l/r channel samples
        samplerate, samples = read(tmpfile)
        samples_per_frame = samplerate / fps
        total_frames = len(samples) // samples_per_frame
        print(
            f"{samplerate=}, {samples_per_frame=}",
            f"num of samples={len(samples)} file length={len(samples) / samplerate}",
        )
        print(f"Estimated total frames: {len(samples) // samples_per_frame}")

        samples = samples.astype(float)

        samples[:, 1] = -samples[:, 1]  # flip the y axis
        # map from (-whatever, whatever) to (0, size)
        smallest = samples.min()
        largest = samples.max()
        samples = ((samples - smallest) / (largest - smallest)) * size
        samples = samples.astype(np.uint32)

        thread_out: subprocess.Popen = (
            ffmpeg.output(
                ffmpeg.input("pipe:", format="rawvideo", pix_fmt="rgb24", s=f"{size}x{size}", r=fps).video,
                ffmpeg.input(tmpfile).audio,
                output_file,
                pix_fmt="yuv420p",
            )
            .global_args("-hide_banner", "-loglevel", "error")
            .overwrite_output()
            .run_async(pipe_stdin=True)
        )
        assert thread_out.stdin

        frame_queue = Queue(get_queue_size((size**2) * np.zeros((size, size), dtype=float).itemsize, gb_usage))

        t = Thread(target=generate_lines, args=(samples, samples_per_frame, dissipation, frame_queue))
        t.daemon = True
        t.start()
        frame_counter = tqdm(total=len(samples) // samples_per_frame, unit="f")
        try:
            while True:
                frame = frame_queue.get()
                if frame is None:
                    break

                thread_out.stdin.write(cv2.cvtColor((frame * 255).astype(np.uint8), cv2.COLOR_GRAY2RGB).tobytes())
                frame_counter.update()
                if preview:
                    cv2.imshow("waow", frame)
                    cv2.waitKey(1)

        except KeyboardInterrupt:
            pass
        thread_out.stdin.close()
        thread_out.wait()
