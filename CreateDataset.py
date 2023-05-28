from __future__ import annotations

import multiprocessing.pool as mpp
import os
import sys
import time
from argparse import ArgumentParser
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from glob import glob
from multiprocessing import Pool  # , Process, Queue, current_process
from multiprocessing import freeze_support
from pathlib import Path

import cv2
import dateutil.parser as timeparser
import imagehash
import imagesize
import polars as pl
from cfg_argparser import CfgDict, ConfigArgParser
from PIL import Image
from polars import DataFrame, Expr
from rich.traceback import install
from rich_argparse import ArgumentDefaultsRichHelpFormatter
from tqdm import tqdm
from tqdm.rich import tqdm as rtqdm

from util.print_funcs import ipbar  # , Timer
from util.print_funcs import RichStepper

CPU_COUNT: int = os.cpu_count()  # type: ignore
install()


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
                        help="deletes the output files corresponding to the input files.")
    p_mods.add_argument("--purge_all", action="store_true",
                        help="deletes *every* file in the output directories.")

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
    p_filters.add_argument("--hash-choice", type=str, choices=["ignore_all", "newest", "oldest", "size"],
                           default='size', help="At the chance of a hash conflict, this will decide which to keep.")
    # # ^^ Used for filtering out too old or too new images.
    # p_filters.add_argument("--print-filtered", action="store_true",
    #                        help="prints all images that were removed because of filters.")
    return parser


# byte_format, istarmap, get_file_list, to_recursive
def byte_format(size, suffix="B"):
    '''modified version of: https://stackoverflow.com/a/1094933'''
    if isinstance(size, str):
        size = "".join([val for val in size if val.isnumeric()])
    size = str(size)
    if size != "":
        size = int(size)
        unit = ''
        for unit in [unit, 'Ki', 'Mi', 'Gi', 'Ti']:
            if abs(size) < 2**10:
                return f"{size:3.1f}{unit}{suffix}"
            size /= 2**10
        return f"{size:3.1f}{unit}{suffix}"
    else:
        return f"N/A{suffix}"


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

    return {
        Path(y) for x in (
            glob(str(p), recursive=True)
            for p in folders
        )
        for y in x
    }


def to_recursive(path, recursive) -> Path:
    """Convert the file path to a recursive path if recursive is False
    Ex: i/path/to/image.png => i/path_to_image.png"""
    return Path(path) if recursive else Path(str(path).replace(os.sep, "_"))


class DataFilter:
    '''An abstract DataFilter format, for use in DatasetBuilder.
    '''

    def __init__(self):
        self.mergeable = False
        self.origin = None
        self.filedict = {}  # used for certain filters, like Existing
        self.column_schema = {}
        self.build_schema: dict[str, Expr] | None = None

    def set_origin(self, value):
        self.origin = value

    def compare(self, lst, cols: DataFrame) -> list:
        raise NotImplementedError

    def fast_comp(self) -> Expr:
        raise NotImplementedError

    def __repr__(self):
        attrlist = [
            f"{key}=..." if hasattr(val, "__iter__") and not isinstance(val, str) else f"{key}={val}"
            for key, val in self.__dict__.items()
        ]
        return f"{self.__class__.__name__}({', '.join(attrlist)})"

    def __str__(self):
        return self.__class__.__name__


class StatFilter(DataFilter):
    def __init__(self, beforetime: datetime | None, aftertime: datetime | None):
        super().__init__()
        self.mergeable = True
        self.before = beforetime
        self.after = aftertime
        self.column_schema = {'modifiedtime': pl.Datetime}
        self.build_schema: dict[str, pl.Expr] = {
            'modifiedtime': pl.col('path').apply(lambda x: datetime.fromtimestamp(os.stat(x).st_mtime))  # type: ignore
        }

    def compare(self, lst, cols: pl.DataFrame) -> list:

        files = cols.filter(pl.col('path').is_in(lst))
        files = files.filter(self.fast_comp()
                             )

        return set(files.select('path').to_series())

    def fast_comp(self) -> Expr:
        return (
            pl.when(bool(self.after)).then(
                self.after < pl.col('modifiedtime')
            ).otherwise(True)
            & pl.when(bool(self.before)).then(
                self.before > pl.col('modifiedtime')
            ).otherwise(True)
        )


class ResFilter(DataFilter):
    def __init__(self, minsize: int | None, maxsize: int | None, crop_mod: bool, scale: int):
        super().__init__()
        self.mergeable = True
        self.min: int | None = minsize
        self.max: int | None = maxsize
        self.crop: bool = crop_mod
        self.scale: int = scale
        self.column_schema = {'resolution': pl.List(int)}
        self.build_schema = {'resolution': pl.col('path').apply(lambda x: imagesize.get(x))}

    def compare(self, lst, cols: pl.DataFrame) -> list:
        files = cols.filter(pl.col('path').is_in(lst))
        files = files.filter(self.fast_comp())
        return set(files.select(pl.col('path')).to_series())

    def fast_comp(self) -> Expr:
        if self.crop:
            return (
                pl.when(bool(self.min)).then(
                    pl.col('resolution').apply(lambda l: (min(l) // self.scale) * self.scale >= self.min)
                ).otherwise(True)
                & pl.when(bool(self.max)).then(
                    pl.col('resolution').apply(lambda l: (max(l) // self.scale) * self.scale <= self.max)
                ).otherwise(True)
            )
        else:
            return (
                pl.col('resolution').apply(lambda l: all(dim % self.scale == 0 for dim in l)).all()
                & pl.when(bool(self.min)).then(
                    pl.col('resolution').apply(lambda l: min(l) >= self.min)
                ).otherwise(True)
                & pl.when(bool(self.max)).then(
                    pl.col('resolution').apply(lambda l: max(l) <= self.max)
                ).otherwise(True)
            )


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


class HashFilter(DataFilter):
    def __init__(self, hash_choice, resolver='newest'):
        super().__init__()

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
        self.column_schema = {'hash': str, 'modifiedtime': pl.Datetime}
        self.build_schema: dict[str, pl.Expr] = {
            'hash': pl.col('path').apply(self._hash_img)
        }
        self.data = None

    def compare(self, lst, cols: pl.DataFrame) -> list:
        applied = (
            cols
            # get all files with hashes that correspond to files in lst
            .filter(
                pl.col('hash').is_in(
                    cols.filter(
                        pl.col('path').is_in(lst)
                    ).select(pl.col("hash")).unique().to_series()
                )
            )
            # resolve hash conflicts
            .groupby('hash')
            .apply(
                lambda df: df.filter(self.resolver()) if len(df) > 1 else df
            )
        )

        resolved_paths = set(applied.select(pl.col('path')).to_series())
        return resolved_paths

    # def fast_comp(self) -> Expr:
    #     return (
    #         df

    #         .groupby('hash')
    #         .apply(
    #             lambda df: df.filter(self.resolver()) if len(df) > 1 else df
    #         )
    #     )

    def _hash_img(self, pth):
        return str(self.hasher(Image.open(pth)))

    def _ignore_all(self) -> Path:
        return False

    def _df_with_path_sizes(self, df: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            pl.col("path").apply(lambda p: os.stat(p).st_size).alias('sizes')
        )

    def _accept_newest(self) -> pl.DataFrame:
        return (
            pl.col('modifiedtime') == pl.col('modifiedtime').max()
        )

    def _accept_oldest(self) -> pl.DataFrame:
        return (
            pl.col('modifiedtime') == pl.col('modifiedtime').min()
        )

    def _accept_biggest(self) -> pl.DataFrame:
        sizes = pl.col("path").apply(lambda p: os.stat(p).st_size)
        return (sizes == sizes.max())


class BlacknWhitelistFilter(DataFilter):
    def __init__(self, whitelist=[], blacklist=[]):
        super().__init__()
        self.mergeable = True
        self.whitelist = whitelist
        self.blacklist = blacklist

    def compare(self, lst, cols: pl.DataFrame) -> list:
        out = lst
        if self.whitelist:
            out = self._whitelist(out, self.whitelist)
        if self.blacklist:
            out = self._blacklist(out, self.blacklist)
        return out

    def fast_comp(self) -> Expr:
        args = True
        if self.whitelist:
            for item in self.whitelist:
                args = args & pl.col('path').str.contains(item)

        if self.blacklist:
            for item in self.blacklist:
                args = args & pl.col('path').str.contains(item).is_not()
            # args = args & pl.col('path').is_in(self.blacklist).is_not()
        return args

    def _whitelist(self, imglist, whitelist) -> set:
        return {j for i in whitelist for j in imglist if i in str(j)}

    def _blacklist(self, imglist, blacklist) -> set:
        return set(imglist).difference(self._whitelist(imglist, blacklist))


class ExistingFilter(DataFilter):
    def __init__(self, hr_folder, lr_folder, recursive=True):
        super().__init__()
        self.mergeable = True
        self.existing_list = ExistingFilter._get_existing(hr_folder, lr_folder)
        # print(self.existing_list)
        self.recursive = recursive

    def compare(self, lst, cols: pl.DataFrame) -> list:
        print("Exist")
        for i in lst:
            print(to_recursive(self.filedict[i], self.recursive).with_suffix(""))
        return [
            i
            for i in lst
            if to_recursive(self.filedict[i], self.recursive).with_suffix("") not in self.existing_list
        ]

    def fast_comp(self) -> Expr:
        return (
            pl.col('path').apply(
                lambda p: to_recursive(self.filedict[p], self.recursive).with_suffix("") not in self.existing_list
            )
        )

    @ staticmethod
    def _get_existing(*folders: Path) -> set:
        return set.intersection(*(
            {
                file.relative_to(folder).with_suffix('')
                for file in get_file_list((folder / "**" / "*"))
            }
            for folder in folders
        ))


def starmap(func, args):
    # I'm surprised this isn't built in
    for arg in args:
        yield func(*arg)


def current_time() -> datetime:
    return datetime.fromtimestamp(time.time())


class DatasetBuilder:
    def __init__(self, rich_stepper_object, origin: str, processes=1):
        super().__init__()
        self.filters: list[DataFilter] = []
        self.power = processes
        self.stepper = rich_stepper_object
        self.origin = origin  # necessary for certain filters to work

        self.config = CfgDict("database_config.json", {
            "trim": True,
            'trim_age_limit': 60 * 60 * 24 * 7,
            "trim_check_exists": True,
            "save_interval": 500,
            "chunksize": 100,
            "filepath": "filedb.feather"
        }, autofill=True)
        self.filepath = self.config['filepath']
        self.time_threshold = self.config['trim_age_limit']

        self.basic_schema = {
            'path': str,
            'checkedtime': pl.Datetime
        }

        if os.path.exists(self.filepath):
            print("Reading database...")
            self.df = pl.read_ipc(self.config['filepath'], use_pyarrow=True)
            print("Finished.")
        else:
            self.df = pl.DataFrame(schema=self.basic_schema)

    def absolute_dict(self, lst: list[Path]):
        return {(str((self.origin / pth).resolve())): pth for pth in lst}

    def populate_df(self, lst: list[Path]):
        from_full_to_relative = self.absolute_dict(lst)
        abs_paths = from_full_to_relative.keys()

        # build a new schema
        new_schema = dict(self.df.schema).copy()
        build_exprs = dict()
        for f in self.filters:
            f.filedict = from_full_to_relative
            expr = f.build_schema
            if expr is not None:
                build_exprs.update(expr)
            schemas = f.column_schema
            new_schema.update({schema: value
                               for schema, value in schemas.items()
                               if schema not in self.df.schema})

        # add new paths to the dataframe with missing data
        existing_paths = set(self.df.select(pl.col('path')).to_series())
        new_paths = [path for path in abs_paths if path not in existing_paths]
        if new_paths:
            self.df = pl.concat(
                [
                    self.df,
                    pl.DataFrame({
                        'path': new_paths,
                        'checkedtime': [current_time()] * len(new_paths)
                    })
                ],
                how="diagonal"
            )

        # get paths with missing data
        self.df = DatasetBuilder._make_schema_compliant(self.df, new_schema)
        unfinished = self.df.filter(pl.any(pl.col(col).is_null() for col in self.df.columns))
        try:
            if len(unfinished):
                with tqdm(desc="Gathering file info...", total=len(unfinished)) as t:
                    chunksize = self.config['chunksize']
                    save_timer = 0
                    collected_data = pl.DataFrame(schema=new_schema)
                    for df in (
                        unfinished
                        .with_row_count('idx')
                        .with_columns(pl.col('idx') // chunksize)
                        .partition_by('idx')
                    ):
                        df.drop_in_place('idx')
                        new_data = df.with_columns(**{
                            col: pl.when(pl.col(col).is_null()).then(expr).otherwise(pl.col(col))
                            for col, expr in build_exprs.items()
                        })
                        collected_data.vstack(new_data, in_place=True)
                        t.update(len(df))
                        save_timer += chunksize
                        if save_timer > self.config['save_interval']:
                            self.df = self.df.update(collected_data, on='path')
                            self.save_df()
                            t.set_postfix_str(f"Autosaved at {current_time()}")
                            collected_data = collected_data.clear()
                            save_timer = 0

                self.df = self.df.update(collected_data, on='path').rechunk()
                self.save_df()
                self.stepper.print(f"new DB size: [bold yellow]{byte_format(self.get_db_disk_size())}[/bold yellow]")
        except KeyboardInterrupt:
            print("KeyboardInterrupt detected! attempting to save dataframe...")
            self.save_df()
            print("Saved.")
            raise KeyboardInterrupt

        return

    def save_df(self):
        self.df.write_ipc(self.filepath)

    def get_db_disk_size(self):
        """gets the database size on disk."""
        return os.stat(self.config['filepath']).st_size

    @staticmethod
    def _make_schema_compliant(df: pl.DataFrame, schema) -> pl.DataFrame:
        """adds columns from the schema to the dataframe. (not in-place)"""
        return pl.concat(
            [
                df,
                pl.DataFrame(schema=schema)
            ], how="diagonal"
        )

    def add_filters(self, *filters: DataFilter) -> None:
        '''Adds filters to the filter list.'''
        for filter in filters:
            filter.set_origin(self.origin)
            self.filters.append(filter)

    def filter(self, lst: Iterable):
        from_full_to_relative = self.absolute_dict(lst)
        paths = from_full_to_relative.keys()
        with tqdm(self.filters, "Running full filters...") as t:
            vdf = self.df.filter(pl.col('path').is_in(paths))
            comp = True
            count = 0
            for dfilter in self.filters:
                if dfilter.mergeable:
                    comp = comp & dfilter.fast_comp()
                    count += 1
                else:
                    vdf = vdf.filter(
                        comp & pl.col('path').is_in(
                            dfilter.compare(
                                set(vdf.select(pl.col('path')).to_series()),
                                self.df.select(
                                    pl.col('path'),
                                    *[pl.col(col) for col in dfilter.column_schema]
                                )
                            )
                        )
                    )
                    t.update(count + 1)
                    count = 0
                    comp = True
            vdf = vdf.filter(comp)
            t.update(count)
        return [from_full_to_relative[p] for p in vdf.select(pl.col('path')).to_series()]

    def _apply(self, filter_filelist):
        filter, filelist = filter_filelist
        return filter.apply(filelist)

    def __enter__(self, *args, **kwargs):
        self.__init__(*args, **kwargs)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        pass


@dataclass
class DatasetFile:
    path: Path
    hr_path: Path
    lr_path: Path


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


def main(args):

    s = RichStepper(loglevel=1, step=-1)
    s.next("Settings: ")

    args.input = Path(args.input)

    df = DatasetBuilder(
        s,
        origin=str(args.input),
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

        df.add_filters(StatFilter(args.before, args.after))

    args.minsize = args.minsize if args.minsize != -1 else None
    args.maxsize = args.maxsize if args.maxsize != -1 else None
    df.add_filters(ResFilter(args.minsize, args.maxsize, args.crop_mod, args.scale))

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
    s.print(f"Searching extensions: {args.exts}")
    file_list = get_file_list(*[args.input / "**" / f"*.{ext}" for ext in args.exts])
    image_list = set(map(lambda x: x.relative_to(args.input), sorted(file_list)))
    if args.image_limit and args.limit_mode == "before":  # limit image number
        image_list = set(list(image_list)[:args.image_limit])

    s.print(f"Gathered {len(image_list)} images")

# * Hashing option
    if args.hash:
        df.add_filters(HashFilter(args.hash_type, args.hash_choice))

# * white / blacklist option
    if args.whitelist or args.blacklist:
        whitelist = []
        blacklist = []
        if args.whitelist:
            whitelist = args.whitelist.split(args.list_separator)
        if args.blacklist:
            blacklist = args.blacklist.split(args.list_separator)
        df.add_filters(BlacknWhitelistFilter(whitelist, blacklist))


# * Purge existing images
    if args.purge_all:
        lst = get_file_list(hr_folder / "**" / "*",
                            lr_folder / "**" / "*")
        if lst:
            s.next("Purging...")
            for file in ipbar(lst):
                if file.is_file():
                    file.unlink()
            for folder in ipbar(lst):
                if folder.is_dir():
                    folder.rmdir()
            s.print("Purged.")
    elif args.purge:
        s.next("Purging...")
        for path in ipbar(image_list):
            hr_path, lr_path = hrlr_pair(path, hr_folder, lr_folder, args.recursive, args.extension)
            hr_path.unlink(missing_ok=True)
            lr_path.unlink(missing_ok=True)
        s.print("Purged.")

    if not args.overwrite:
        df.add_filters(ExistingFilter(hr_folder, lr_folder, args.recursive))


# * Run filters
    s.next("Populating df...")
    df.populate_df(image_list)

    s.next("Filtering using:")
    if df.filters:
        s.print(
            *[f' - {str(filter)}' for filter in df.filters]
        )
        image_list = set(df.filter(image_list))

    if not check_for_images(image_list):
        return 0

    if args.image_limit and args.limit_mode == "after":
        image_list = set(image_list[:args.image_limit])

    if args.simulate:
        s.next(f"Simulated. {len(image_list)} images remain.")
        return 0


# * convert files. Finally!
    s.next("Converting...")
    image_list: set[Path] = {Path(p) for p in image_list}
    try:
        pargs = [
            (DatasetFile(
                args.input / v,
                *hrlr_pair(v, hr_folder, lr_folder, args.recursive, args.extension)
            ),
                args.scale)
            for v in image_list
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
    freeze_support()
    cparser = ConfigArgParser(main_parser(), "config.json", exit_on_change=True)
    args = cparser.parse_args()
    if args.perfdump:
        main = wrap_profiler(main, filename='CreateDataset.prof')

    main(args)
