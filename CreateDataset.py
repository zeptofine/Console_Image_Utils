from __future__ import annotations

import time
from collections.abc import Callable, Generator, Iterable
from dataclasses import dataclass
from enum import Enum

'''
    Conversion script from folder to hr/lr pair.
    Author: Zeptofine
'''
import multiprocessing.pool as mpp
import os
import random
import sys
from argparse import ArgumentParser
from datetime import datetime
from glob import glob
from multiprocessing import Pool  # , Process, Queue, current_process
from pathlib import Path

import cv2
import dateutil.parser as timeparser
import imagehash
import imagesize
import pandas as pd
from cfg_argparser import CfgDict, ConfigArgParser
from PIL import Image
from rich.traceback import install
from rich_argparse import ArgumentDefaultsRichHelpFormatter
from tqdm import tqdm
from tqdm.rich import tqdm as rtqdm

from util.print_funcs import ipbar  # , Timer
from util.print_funcs import RichStepper

install()

CPU_COUNT: int = os.cpu_count()  # type: ignore

if sys.platform == "win32":
    print("This application was not made for windows. Try Using WSL2")
    from time import sleep
    sleep(3)


def main_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="CreateDataset.py",
        formatter_class=ArgumentDefaultsRichHelpFormatter,
        description="""Hi! this script converts thousands of files to
    another format in a High-res/Low-res pairs for data science.
    @ is available to follow a file.""",
        fromfile_prefix_chars="@")

    import shtab
    shtab.add_argument_to(parser)

    p_reqs = parser.add_argument_group("Runtime")
    p_reqs.add_argument("-i", "--input",
                        help="Input folder.", required=True)
    p_reqs.add_argument("-x", "--scale", type=int, default=4,
                        help="scale to downscale LR images")
    p_reqs.add_argument("-e", "--extension", metavar="EXT", default=None,
                        help="export extension.")
    p_reqs.add_argument("--exts", default="png webp jpg",
                        help="extensions to search for. Only images work currently.")
    p_mods = parser.add_argument_group("Modifiers")
    p_mods.add_argument("-r", "--recursive", action="store_true", default=False,
                        help="preserves the tree hierarchy.")
    p_mods.add_argument("-t", "--threads", type=int, default=int((CPU_COUNT / 4) * 3),
                        help="number of total threads used for multiprocessing.")
    p_mods.add_argument("-l", "--image_limit", type=int, default=None, metavar="MAX",
                        help="only gathers a given number of images. None disables it entirely.")  # max numbers to be given to the filters
    p_mods.add_argument("--limit_mode", choices=["before", "after"], default="before",
                        help="Changes the order of the limiter. By default, it happens before filtering out bad images.")
    # ^^ this choice is for if you want to convert n images, or only search n images.
    p_mods.add_argument("--simulate", action="store_true",
                        help="skips the conversion step. Used for debugging.")
    p_mods.add_argument("--purge", action="store_true",
                        help="Clears the output folder before running.")
    p_mods.add_argument("--reverse", action="store_true",
                        help="reverses the sorting direction. it turns smallest-> largest to largest -> smallest")
    p_mods.add_argument("--overwrite", action="store_true",
                        help="Skips checking for existing files, and by proxy, overwrites existing files.")
    p_mods.add_argument("--perfdump", action="store_true",
                        help="Dumps performance information for reading with snakeviz or others.")
    # certain criteria that images must meet in order to be included in the processing.
    p_filters = parser.add_argument_group("Filters")
    p_filters.add_argument("-w", "--whitelist", type=str, metavar="INCLUDE",
                           help="only allows paths with the given string.")
    p_filters.add_argument("-b", "--blacklist", type=str, metavar="EXCLUDE",
                           help="excludes paths with the given string.")
    p_filters.add_argument("--list_separator", default=" ",
                           help="separator for the white/blacklist.")
    # ^^ used for restricting the names allowed in the paths.

    p_filters.add_argument("--minsize", type=int, metavar="MIN", default=128,
                           help="smallest available image")
    p_filters.add_argument("--maxsize", type=int, metavar="MAX",
                           help="largest allowed image.")
    p_filters.add_argument("--crop_mod", action="store_true",
                           help="changes mod mode so that it crops the image to an image that actually is divisible by scale, typically by a few px")
    # ^^ used for filtering out too small or too big images.
    p_filters.add_argument("--after", type=str,
                           help="Only uses files modified after a given date."
                           "ex. '2020', or '2009 Sept 16th'")
    p_filters.add_argument("--before", type=str,
                           help="Only uses before a given date. ex. 'Wed Jun 9 04:26:40', or 'Jun 9'")
    p_filters.add_argument("--keep_links", action="store_true",
                           help="Keeps links in the file list. Is useful if the dataset is messy regarding sym/hardlinks.")
    p_filters.add_argument("--hash", action="store_true",
                           help="Removes similar images. is better for perceptually similar images.")
    p_filters.add_argument("--hash-type", type=str, choices=["average", "crop_resistant", "color", "dhash", "dhash_vertical",
                                                             "phash", "phash_simple", "whash"], default="average",
                           help="type of image hasher to use for the slow method. read https://github.com/JohannesBuchner/imagehash for more info")
    # {
    #         'ignore_all': self._ignore_all,
    #         'newest': self._accept_newest,
    #         'oldest': self._accept_oldest
    #     }
    p_filters.add_argument("--hash-choice", type=str, choices=["ignore_all", "newest", "oldest", "size"],
                           default='size', help="At the chance of a hash conflict, this will decide which to keep.")
    # # ^^ Used for filtering out too old or too new images.
    # p_filters.add_argument("--print-filtered", action="store_true",
    #                        help="prints all images that were removed because of filters.")
    return parser


def istarmap(self, func, iterable, chunksize=1):
    """starmap-version of imap
    """
    self._check_running()  # type: ignore
    if chunksize < 1:
        raise ValueError(
            "Chunksize must be 1+, not {0:n}".format(
                chunksize))

    task_batches = mpp.Pool._get_tasks(  # type: ignore
        func, iterable, chunksize)
    result = mpp.IMapIterator(self)
    self._taskqueue.put(  # type: ignore
        (
            self._guarded_task_generation(result._job,  # type: ignore
                                          mpp.starmapstar,  # type: ignore
                                          task_batches),
            result._set_length  # type: ignore
        ))
    return (item for chunk in result for item in chunk)


def get_file_list(*folders: Path) -> list[Path]:
    """
    Args    folders: One or more folder paths.
    Returns list[Path]: paths in the specified folders."""
    i = tqdm(folders) if len(folders) > 1 else folders

    return [
        Path(y) for x in (
            glob(str(p), recursive=True)
            for p in i
        )
        for y in x
    ]


def get_existing(*folders: Path) -> set:
    """
    Returns the files that already exist in the specified folders.
    Args    *: folders to be searched & compared.
    Returns tuple[set[Path], set[Path]]: HR and LR file paths in sets.
    """
    return set.intersection(*(
        {
            file.relative_to(folder).with_suffix('')
            for file in get_file_list((folder / "**" / "*"))
        }
        for folder in folders
    ))


def has_links(paths) -> bool:
    return any(i for i in paths if i is not i.resolve())


def to_recursive(path, recursive) -> Path:
    """Convert the file path to a recursive path if recursive is False
    Ex: i/path/to/image.png => i/path_to_image.png"""
    return Path(path) if recursive else Path(str(path).replace(os.sep, "_"))


IMHASH_TYPES = {
    'average': imagehash.average_hash,
    'crop_resistant': imagehash.crop_resistant_hash,
    'color': imagehash.colorhash,
    'dhash': imagehash.dhash,
    'dhash_vertical': imagehash.dhash_vertical,
    'phash': imagehash.phash,
    'phash_simple': imagehash.phash_simple,
    'whash': imagehash.whash
}


def hrlr_pair(path: Path, hr_folder: Path, lr_folder: Path,
              recursive: bool = False, ext=None) -> tuple[Path, Path]:
    """
    gets the HR and LR file paths for a given file or directory path.
    Args    recursive (bool): Whether to search for the file in subdirectories.
            ext (str): The file extension to append to the file name.
    Returns tuple[Path, Path]: HR and LR file paths.
    """
    hr_path = hr_folder / to_recursive(path, recursive)
    lr_path = lr_folder / to_recursive(path, recursive)
    # Create the HR and LR folders if they do not exist
    hr_path.parent.mkdir(parents=True, exist_ok=True)
    lr_path.parent.mkdir(parents=True, exist_ok=True)
    # If an extension is provided, append it to the HR and LR file paths
    if ext:
        hr_path = hr_path.with_suffix(f".{ext}")
        lr_path = lr_path.with_suffix(f".{ext}")
    return hr_path, lr_path


def hash_img(img, hasher):
    return hasher(Image.open(img))


@dataclass
class DatasetFile:
    path: Path
    hr_path: Path
    lr_path: Path


# def fileparse(inpath: Path, source: Path, scale: int,
#               hr_folder: Path, lr_folder: Path) -> Path:
def fileparse(dfile: DatasetFile, scale):
    """Converts an image file to HR and LR versions and saves them to the specified folders.
    """
    # Read the image file
    image = cv2.imread(str(dfile.path), cv2.IMREAD_UNCHANGED)
    image = image[0:(image.shape[0] // scale) * scale,
                  0:(image.shape[1] // scale) * scale]
    # Save the HR / LR version of the image
    cv2.imwrite(str(dfile.hr_path), image)
    cv2.imwrite(str(dfile.lr_path), cv2.resize(image, (0, 0),
                                               fx=1 / scale, fy=1 / scale))  # type: ignore

    # Set the modification time of the HR and LR image files to the original image's modification time
    mtime = dfile.path.stat().st_mtime
    os.utime(str(dfile.hr_path), (mtime, mtime))
    os.utime(str(dfile.lr_path), (mtime, mtime))


class DatasetBuilder:
    def __init__(self, rich_stepper_object, origin: str = None, processes=1):
        super().__init__()
        self.filters: list[DataFilter] = []
        self.full_filters: list[DataFilter] = []
        self.power = processes
        self.stepper = rich_stepper_object
        self.origin = origin  # necessary for certain filters to work

    def add_filters(self, *filters: DataFilter) -> None:
        '''Adds filters to the filter list.
        '''
        for filter in filters:
            filter.set_parent(self)
            filter.set_origin(self.origin)
            if filter.type == FilterTypes.PER_ITEM:
                self.filters.append(filter)
            else:
                self.full_filters.append(filter)

    def run_filters(self, x):
        return all(filter.compare(x) for filter in self.filters)

    def map(self, lst: Iterable, use_pool: bool = False) -> Iterable[bool]:
        '''Maps all input to all the filters.

        Parameters
        ----------
        lst : Iterable
            the iterable to run through.
        use_pool : bool
            whether or not to use a pool. defaults to False
        Yields
        ------
        Iterable[bool]
            every result for every list
        '''
        if use_pool:
            p = Pool(self.power)
            iterable = p.imap(self.run_filters, lst)
        else:
            p = None
            iterable = map(self.run_filters, lst)
        for result in tqdm(iterable, "Running filters..."):
            yield result
        # with tqdm(desc="Running filters...") as t:
        #     for result in iterable:
        #         yield result
        #         t.update()
        #     t.close()
        if p:
            p.close()

    def full_map(self, lst: Iterable, use_pool: bool = True):
        if use_pool:
            p = Pool(self.power)
        else:
            p = None
        for filter in tqdm(self.full_filters, "Running full filters..."):
            lst = filter.full_compare(lst, p)
        if p:
            p.close()
        return lst

    def filter(self, lst: Iterable, cond: Callable = lambda x: x, use_pool=False) -> Generator:
        '''A version of map that only yields successful results
        '''
        return (file for result, file in zip(self.map(lst, use_pool=use_pool), lst) if cond(result))

    def _apply(self, filter_filelist):
        filter, filelist = filter_filelist
        return filter.apply(filelist)

    def __enter__(self, *args, **kwargs):
        self.__init__(*args, **kwargs)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.filters.clear()
        del self.filters
        pass


class FilterTypes(Enum):
    PER_ITEM = 1
    FULL = 2


class DataFilter:
    '''An abstract DataFilter format, for use in DatasetBuilder.
    '''

    def __init__(self):
        self.parent = None
        self.type = FilterTypes.PER_ITEM
        self.origin = None

    def set_origin(self, value):
        self.origin = value

    def set_parent(self, parent: DatasetBuilder):
        self.parent = parent

    def compare(self, file: Path) -> bool:
        raise NotImplementedError

    def full_compare(self, lst: Iterable[Path], p: Pool = None) -> list:
        raise NotImplementedError

    def __repr__(self):
        attrlist = [
            f"{key}=..." if hasattr(val, "__iter__") and not isinstance(val, str) else f"{key}={val}"
            for key, val in self.__dict__.items()
        ]
        return f"{self.__class__.__name__}({', '.join(attrlist)})"

    def __str__(self):
        return self.__class__.__name__


class FilterStat(DataFilter):
    def __init__(self, beforetime: datetime | None, aftertime: datetime | None):
        super().__init__()
        self.before = beforetime
        self.after = aftertime

    def compare(self, file: Path) -> bool:
        st_mtime = datetime.fromtimestamp(file.stat().st_mtime)
        return not ((self.after and self.after < st_mtime) or (self.before and self.before > st_mtime))


class FilterRes(DataFilter):
    def __init__(self, minsize: int | None, maxsize: int | None, crop_mod: bool, scale: int):
        super().__init__()
        self.min: int | None = minsize
        self.max: int | None = maxsize
        self.crop: bool = crop_mod
        self.scale: int = scale

    def compare(self, file: Path) -> bool:
        res = imagesize.get(file)
        if self.crop:
            res = (res[0] // self.scale) * self.scale, (res[1] // self.scale) * self.scale
        minsize, maxsize = self.min or min(res), self.max or max(res)

        return all(dim % self.scale == 0 and minsize <= dim <= maxsize for dim in res)


class FilterHash(DataFilter):
    def __init__(self, hash_choice, resolver='newest'):
        self.type = FilterTypes.FULL

        IMHASH_RESOLVERS = {
            'ignore_all': self._ignore_all,
            'newest': self._accept_newest,
            'oldest': self._accept_oldest,
            'size': self._accept_biggest
        }
        if hash_choice not in IMHASH_TYPES:
            raise KeyError(f"{hash_choice} is not in IMHASH_TYPES")
        if resolver not in IMHASH_RESOLVERS:
            raise KeyError(f"{resolver} is not in IMHASH_RESOLVERS")
        self.hasher = IMHASH_TYPES[hash_choice]
        self.resolver = IMHASH_RESOLVERS[resolver]
        self.settings = CfgDict("hashing_config.json", {
            "trim": True,
            "trim_age_limit": 60 * 60 * 24 * 7,
            "filepath": "hashes.h5"
        }, autofill=True)
        self.filepath = self.settings['filepath']
        if os.path.exists(self.filepath):
            print("Reading hash database...")
            self.dataframe = pd.read_hdf(self.filepath, 'table')
            print("Finished.")
        else:
            self.dataframe = pd.DataFrame(columns=['path', 'hash', 'modifiedtime', 'checkedtime'])

    def full_compare(self, lst: list[Path], p: Pool = None) -> list:
        lst = set(sorted(lst, key=lambda _: random.random()))

        from_full_to_relative = {(self.origin / pth).resolve(): pth for pth in lst}

        resolved_lst = from_full_to_relative.keys()

        # drop hashes that are too old or the modification time changed
        if self.settings['trim']:
            original_size = len(self.dataframe)
            maxduration_s = self.settings['trim_age_limit']  # 7 days

            current_time = time.time()
            list_to_hash = []
            for idx, row in tqdm(self.dataframe.iterrows(), "Trimming db...", total=len(self.dataframe)):
                if (not os.path.exists(row['path'])
                    or Path(row['path']).stat().st_mtime != row['modifiedtime']
                        or row['checkedtime'] < current_time - maxduration_s):
                    list_to_hash.append((idx, row['path']))

            self.dataframe.drop(map(lambda x: x[0], list_to_hash), inplace=True)
            if len(self.dataframe) != original_size:
                print(f"stripped old/invalid hashes from list. new hashlist length: {len(self.dataframe)}")

        conv_lst = []
        hashed_lst = set(map(Path, self.dataframe['path']))
        conv_lst = [path for path in resolved_lst if path not in hashed_lst]
        if conv_lst:
            print(f"Getting hashes for {len(conv_lst)} images")
            if p:
                iterable = zip(
                    conv_lst,
                    istarmap(p, hash_img, zip(conv_lst, [self.hasher]*len(conv_lst))),
                )
            else:
                iterable = zip(
                    conv_lst,
                    map(lambda p: hash_img(p, self.hasher), conv_lst),
                )

            for pth, h in tqdm(iterable, "Gathering...", total=len(conv_lst)):
                stat = pth.stat()
                self.dataframe.loc[len(self.dataframe.index)] = [str(pth.resolve()), str(h), stat.st_mtime, time.time()]

            self.dataframe.to_hdf(self.filepath, 'table')

        resolved_paths = []

        strlst = map(str, resolved_lst)
        path_rows = self.dataframe.loc[self.dataframe['path'].isin(strlst)]
        hashes = set(path_rows['hash'])
        paths_with_identical_hashes = self.dataframe.loc[self.dataframe['hash'].isin(hashes)]
        for h, group in tqdm(paths_with_identical_hashes.groupby('hash').groups.items(), "Grouping..."):
            if len(group) > 1:
                rows = list(self.dataframe.iloc[group]['path'])
                resolved = self.resolver(rows)
                if resolved is not None:
                    resolved_paths.append(Path(resolved))
                    # rprint(f"{rows} -> '{resolved}'")
            elif len(group) == 1:
                resolved_paths.append(Path(list(self.dataframe.iloc[group]['path'])[0]))
            else:
                raise RuntimeError("What")

        return [from_full_to_relative[i] for i in resolved_paths if i in from_full_to_relative]

    def _ignore_all(self, _) -> Path:
        return None

    def _get_ages(self, lst) -> dict:
        return {pth: Path(pth).stat().st_mtime for pth in lst}

    def _get_sizes(self, lst) -> dict:
        return {pth: Path(pth).stat().st_size for pth in lst}

    def _accept_newest(self, lst) -> Path:
        return sorted(self._get_ages(lst).items(), key=lambda p_a: p_a[::-1])[-1][0]

    def _accept_oldest(self, lst) -> Path:
        return sorted(self._get_ages(lst).items(), key=lambda p_a: p_a[::-1])[0][0]

    def _accept_biggest(self, lst) -> Path:
        return sorted(self._get_sizes(lst).items(), key=lambda s_p: s_p[::-1])[-1][0]


class FilterBlacknWhitelist(DataFilter):
    def __init__(self, whitelist=[], blacklist=[]):
        self.type = FilterTypes.FULL
        self.whitelist = whitelist
        self.blacklist = blacklist

    def full_compare(self, lst: Iterable[Path], p: Pool = None) -> list:
        out = lst
        if self.whitelist:
            out = self._whitelist(out, self.whitelist)
            print(f"whitelist {self.whitelist}: {len(out)}")
        if self.blacklist:
            out = self._blacklist(out, self.blacklist)
            print(f"blacklist {self.blacklist}: {len(out)}")

        return out

    def _whitelist(self, imglist, whitelist) -> set:
        return {j for i in whitelist for j in imglist if i in str(j)}

    def _blacklist(self, imglist, blacklist) -> set:
        return set(imglist).difference(self._whitelist(imglist, blacklist))


class FilterExisting(DataFilter):
    def __init__(self, hr_folder, lr_folder, recursive=True):
        self.type = FilterTypes.FULL
        self.existing_list = get_existing(hr_folder, lr_folder)
        self.recursive = recursive

    def full_compare(self, lst: Iterable[Path], _=None) -> list:
        return [
            i
            for i in tqdm(lst, "Removing existing images...")
            if to_recursive(i, self.recursive).with_suffix("") not in self.existing_list
        ]


class FilterLinks(DataFilter):
    def __init__(self):
        self.type = FilterTypes.FULL

    def full_compare(self, lst: Iterable[Path], p: Pool = None) -> list:
        return set({
            (self.origin / pth).resolve(): pth
            for pth in tqdm(lst, "Resolving links...")
        }.values())


def starmap(func, args):
    # I'm surprised this isn't built in
    for arg in args:
        yield func(*arg)


def main(args):

    s = RichStepper(loglevel=1, step=-1)
    s.next("Settings: ")

    args.input = Path(args.input)

    df = DatasetBuilder(
        s,
        origin=args.input,
        processes=args.threads
    )

    def check_for_images(image_list) -> bool:
        if not image_list:
            s.print(-1, "No images left to process")
            return False
        return True

# * Make sure given args are valid
    if args.extension:
        if args.extension.startswith("."):
            args.extension = args.extension[1:]
        if args.extension.lower() in ["self", "none", "same", ""]:
            args.extension = None
    if args.after or args.before:
        try:
            if args.after:
                args.after = timeparser.parse(str(args.after))
            if args.before:
                args.before = timeparser.parse(str(args.before))
            if args.after and args.before and args.after > args.before:
                raise timeparser.ParserError(
                    f"{args.before} (--before) is older than {args.after} (--after)!")
        except timeparser.ParserError as err:
            s.set(-9).print(str(err))
            return 1

        df.add_filters(FilterStat(args.before, args.after))

    args.minsize = args.minsize if args.minsize != -1 else None
    args.maxsize = args.maxsize if args.maxsize != -1 else None
    df.add_filters(FilterRes(args.minsize, args.maxsize, args.crop_mod, args.scale))

    if args.before or args.after:
        s.print(f"Filtering by time ({args.before} <= x <= {args.after})")
    if args.minsize or args.maxsize:
        s.print(f"Filtering by size ({args.minsize} <= x <= {args.maxsize})")

    args.input = Path(args.input)


# * Get hr / lr folders
    hr_folder = args.input.parent / f"{str(args.scale)}xHR"
    lr_folder = args.input.parent / f"{str(args.scale)}xLR"
    if args.extension:
        hr_folder = Path(f"{str(hr_folder)}-{args.extension}")
        lr_folder = Path(f"{str(lr_folder)}-{args.extension}")
    hr_folder.parent.mkdir(parents=True, exist_ok=True)
    lr_folder.parent.mkdir(parents=True, exist_ok=True)

# * Gather images
    s.next("Gathering images...")
    args.exts = args.exts.split(" ")
    s.print(f"Searched extensions: {args.exts}")
    file_list = get_file_list(*[args.input / "**" / f"*.{ext}" for ext in args.exts])
    image_list = set(map(lambda x: x.relative_to(args.input), sorted(file_list)))
    if args.image_limit and args.limit_mode == "before":  # limit image number
        image_list = image_list[:args.image_limit]

    s.print(f"Gathered {len(image_list)} images")

    s.next()

# * Discard symbolic duplicates
    if not args.keep_links:
        df.add_filters(FilterLinks())

# * Hashing option
    if args.hash:
        df.add_filters(FilterHash(args.hash_type, args.hash_choice))

# * white / blacklist option
    if args.whitelist or args.blacklist:
        whitelist = []
        blacklist = []
        if args.whitelist:
            whitelist = args.whitelist.split(args.list_separator)
        if args.blacklist:
            blacklist = args.blacklist.split(args.list_separator)
        df.add_filters(FilterBlacknWhitelist(whitelist, blacklist))


# * Purge existing images
    if args.purge:
        s.next("Purging...")

        for path in ipbar(image_list):
            hr_path, lr_path = hrlr_pair(path, hr_folder, lr_folder, args.recursive, args.extension)
            hr_path.unlink(missing_ok=True)
            lr_path.unlink(missing_ok=True)

        s.print("Purged.")

    if not args.overwrite:
        df.add_filters(FilterExisting(hr_folder, lr_folder, args.recursive))


# * Run filters
    if df.full_filters:
        s.print(
            "Filtering using: ",
            *[f' - {str(filter)}' for filter in df.full_filters]
        )
        image_list = df.full_map(image_list, use_pool=True)

    if not check_for_images(image_list):
        return 0

    if df.filters:
        s.print(
            "Filtering using: ",
            *[f" - {str(filter)}" for filter in df.filters]
        )
        results = df.map({*map(lambda x: args.input / x, image_list), })
        image_list = [i[0] for i in zip(image_list, results) if i[1]]

    if not check_for_images(image_list):
        return 0

    if args.image_limit and args.limit_mode == "after":
        image_list = set(image_list[:args.image_limit])

    if args.simulate:
        s.next(f"Simulated. {len(image_list)} images remain.")
        return 0

# * convert files. Finally!
    s.next("Converting...")
    image_list: list[Path] = [Path(p) for p in image_list]
    try:
        pargs = [
            (DatasetFile(args.input / v,
                         *hrlr_pair(v, hr_folder, lr_folder, args.recursive, args.extension)), args.scale) for v in image_list
        ]
        with Pool(args.threads) as p:
            for _ in rtqdm(istarmap(p, fileparse, pargs), total=len(image_list)):
                pass

    except KeyboardInterrupt:
        s.print(-1, "KeyboardInterrupt")


def wrap_profiler(func, filename):
    import cProfile
    import pstats

    def _wrapped(*args, **kwargs):
        with cProfile.Profile() as pr:
            func(*args, **kwargs)
        stats = pstats.Stats(pr)
        stats.sort_stats(pstats.SortKey.TIME)
        stats.dump_stats(filename=filename)
        print("Performance dumped.")
    return _wrapped


if __name__ == "__main__":
    cparser = ConfigArgParser(main_parser(), "config.json", exit_on_change=True)
    args = cparser.parse_args()
    if args.perfdump:
        main = wrap_profiler(main, filename='CreateDataset.prof')

    main(args)
