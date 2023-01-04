import os
from re import compile as rcompile

ansi_escape = rcompile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def p_bar(iteration: int, total: int, length=20,
          fill="#", nullp="-", corner="[]", pref='', suff='') -> str:
    filledLength = (length * iteration) // total
    #    [#############################]
    pbar = (fill*length)[:filledLength] + (nullp*(length - filledLength))
    command = f"{str(pref)}\033[92m{corner[0]}\033[93m{pbar}\033[92m{corner[1]}\033[0m{str(suff)}"
    return command


def thread_status(pid: int, item: str = "", extra: str = "", anonymous: bool = False,
                  item_size=None) -> None:
    len_extra = len(ansi_escape.sub('', extra))
    item_size = item_size if item_size else os.get_terminal_size().columns
    output = f"{pid}: "
    output += f"{item}" if not anonymous else ""
    output = output[:item_size-len_extra-2]
    output += (" "*item_size + extra)[len(output)+len_extra+1:]
    output = f"{'\n'*pid}{output}{'\033[A'*pid}"
    print(output, end="\r")

class Timer:
    def __init__(self):
        self.reset()
        
    def print(self, msg):
        self.poll(msg)
        self.reset()
        return self
    
    def poll(self, msg):
        print(f"{time.perf_counter() - self.time}: {msg}")
        return self

    def reset(self):
        self.time = time.perf_counter()
        return self.time
        return self
