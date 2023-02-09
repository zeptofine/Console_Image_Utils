
import multiprocessing
import multiprocessing.pool as mpp

from tqdm import tqdm

# Mostly taken from: https://stackoverflow.com/a/57364423
pool = multiprocessing.Pool()


class CustomPool(pool.__class__):
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


pool.close()
del pool


def poolmap(threads, func, iterable, use_tqdm=True, chunksize=1, refresh=False, postfix=True, **tqargs) -> list:
    with CustomPool(min(threads, len(iterable))) as pool:
        if use_tqdm:
            itqdm = tqdm(total=len(iterable), dynamic_ncols=True,
                         position=0, **tqargs)
            for result in pool.istarmap(  # type: ignore
                    func, iterable, chunksize=chunksize):
                if postfix:
                    itqdm.set_postfix_str(
                        str(result), refresh=False)
                yield result
                itqdm.update()
                if refresh:
                    itqdm.refresh()
        else:
            for result in pool.istarmap(func,  # type: ignore
                                        iterable):
                yield result
