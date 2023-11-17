import argparse
import contextlib
import subprocess
from collections.abc import Generator
from itertools import islice
from queue import Queue
from threading import Thread
from typing import Callable

import cv2
import ffmpeg
import numpy as np


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


def iterate_none_delimited_queue(q: Queue):
    while True:
        item = q.get()
        if item is None:
            break
        yield item


def generate_lines(
    in_q: Queue[np.ndarray],
    samples_per_frame: int,
    dissipation: float,
    out_q: Queue[np.ndarray | None],
):
    canvas = np.zeros((size, size), dtype=float)
    samplecount = 1

    def iterate():
        def get_caster(points):
            info = np.iinfo(points.dtype)
            mi, ma = info.min, info.max

            def transformer(pts):
                return (pts - mi) / (ma - mi) * size

            return transformer

        caster: Callable | None = None
        for points in iterate_none_delimited_queue(in_q):
            if caster is None:
                caster = get_caster(points)

            points = points.astype(float)
            points[:, 1] = -points[:, 1]
            points: np.ndarray = caster(points).astype(np.int32)

            yield from points

    for pts in window(iterate(), 2):
        cv2.line(canvas, pts[0], pts[1], (1, 1, 1), 1)

        samplecount += 1
        if samplecount >= samples_per_frame:
            out_q.put(canvas.copy())
            canvas *= dissipation
            samplecount = 0
    out_q.put(None)

    # samples[:, 1] = -samples[:, 1]  # flip the y axis
    # # map from (-whatever, whatever) to (0, size)
    # smallest = samples.min()
    # largest = samples.max()
    # samples = ((samples - smallest) / (largest - smallest)) * size
    # samples = samples.astype(np.uint32)


def chunked_io_reader(stream: subprocess.Popen, chunk_size: int = 10**6) -> Generator[bytes, None, None]:
    assert stream.stdout is not None
    while True:
        chunk = stream.stdout.read(chunk_size)
        if not chunk:
            break
        yield chunk


def stream_iterator(stream: subprocess.Popen, samplerate=96000):
    print("started chunking")
    for chunk in chunked_io_reader(stream, samplerate * 100):
        yield np.frombuffer(chunk, dtype="int16").reshape((-1, 2))
    yield None


def stream_handler(ffmpeg_command, samplerate, out_q: Queue[np.ndarray | None]):
    stream: subprocess.Popen = ffmpeg_command.run_async(pipe_stdout=True)
    for chunk in stream_iterator(stream, samplerate):
        out_q.put(chunk)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--output", "-o", default="output.mkv")
    parser.add_argument("--fps", "-r", type=int, default=48)
    parser.add_argument("--samplerate", type=int, default=96000)
    parser.add_argument("--size", "-s", type=int, default=800)
    parser.add_argument("--dissipation", "-d", type=float, default=0.75)
    parser.add_argument("--preview", action="store_true", default=False)
    args = parser.parse_args()

    input_file: str = args.file
    output_file: str = args.output
    fps: int = args.fps
    samplerate: int = args.samplerate
    size: int = args.size
    dissipation: int = args.dissipation
    preview: bool = args.preview

    samples_per_frame = samplerate / fps
    stream = ffmpeg.output(
        ffmpeg.input(input_file),
        "-",
        f="s16le",
        acodec="pcm_s16le",
        ac=2,
        ar=samplerate,
    ).global_args("-hide_banner", "-loglevel", "error")

    thread_out: subprocess.Popen = (
        ffmpeg.output(
            ffmpeg.input("pipe:", format="rawvideo", pix_fmt="rgb24", s=f"{size}x{size}", r=fps).video,
            ffmpeg.input(input_file).audio,
            output_file,
            pix_fmt="yuv420p",
        )
        # .global_args("-hide_banner", "-loglevel", "error")
        .overwrite_output().run_async(pipe_stdin=True)
    )
    assert thread_out.stdin

    in_q = Queue(100)

    frame_queue = Queue(20)

    reader_thread = Thread(target=stream_handler, args=(stream, samplerate, in_q))
    reader_thread.daemon = True
    reader_thread.start()

    t = Thread(target=generate_lines, args=(in_q, samples_per_frame, dissipation, frame_queue))
    t.daemon = True
    t.start()
    # for chunk in chunked_io_reader(stream, samplerate * 10):
    #     arr = np.frombuffer(chunk, dtype="int16").reshape((-1, 2))
    with contextlib.suppress(KeyboardInterrupt):
        while True:
            frame = frame_queue.get()
            if frame is None:
                break

            thread_out.stdin.write(cv2.cvtColor((frame * 255).astype(np.uint8), cv2.COLOR_GRAY2RGB).tobytes())

            if preview:
                cv2.imshow("waow", frame)
                cv2.waitKey(1)

    cv2.destroyAllWindows()
    thread_out.stdin.close()
    thread_out.wait()
