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
from scipy.io.wavfile import read
from tqdm import tqdm

parser = argparse.ArgumentParser()
parser.add_argument("file")
parser.add_argument("--output", "-o", default="output.mkv")
parser.add_argument("--fps", "-r", type=int, default=48)
parser.add_argument("--size", "-s", type=int, default=800)
parser.add_argument("--dissipation", "-d", type=float, default=0.75)
parser.add_argument("--preview", action="store_true", default=False)
args = parser.parse_args()

input_file = args.file
output_file = args.output
fps = args.fps
size = args.size
dissipation = args.dissipation
preview = args.preview


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
    for pts in window(tqdm(arr), 2):
        cv2.line(canvas, pts[0], pts[1], (1, 1, 1), 1)
        samplecount += 1
        if samplecount >= samples_per_frame:
            out_q.put(canvas.copy())
            canvas *= dissipation
            samplecount = 0

    out_q.put(None)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        tmpfile = tmpdir / "audio.wav"
        ffmpeg.output(ffmpeg.input(input_file), str(tmpfile)).run(quiet=True)

        samplerate: int  # samples / sec
        samples: np.ndarray  # l/r channel samples
        samplerate, samples = read(tmpfile)
        samples_per_frame = samplerate / fps
        print(
            f"{samplerate=}, {samples_per_frame=}, num of samples={len(samples)} file length={len(samples) / samplerate}"
        )
        print(f"Estimated total frames: {len(samples) // samples_per_frame}")

        samples = samples.astype(float)

        samples[:, 1] = -samples[:, 1]  # flip the y axis
        # map from (-whatever, whatever) to (0, size)
        smallest = samples.min()
        largest = samples.max()
        mapped_points = ((samples - smallest) / (largest - smallest)) * size
        mapped_points = mapped_points.astype(np.uint32)

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

        q = Queue(fps * 10)

        t = Thread(target=generate_lines, args=(mapped_points, samples_per_frame, dissipation, q))
        t.daemon = True
        t.start()
        n = 0
        try:
            while True:
                frame = q.get()
                if frame is None:
                    break
                n += 1

                thread_out.stdin.write(cv2.cvtColor((frame * 255).astype(np.uint8), cv2.COLOR_GRAY2RGB).tobytes())
                if preview:
                    cv2.imshow("waow", frame)
                    cv2.waitKey(1)
            print(f"total frames={n}")
        except KeyboardInterrupt:
            pass
        thread_out.stdin.close()
        thread_out.wait()
