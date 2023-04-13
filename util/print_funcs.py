from os import get_terminal_size
import time


def pbar(
    iteration: int, total: int, length=20,
         fill="#", nullp="-", corner="[]", pref='', suff='') -> str:
    filled = (length * iteration) // total
    #    [#############################]
    c1, c2 = "\033[92m", "\033[93m"
    return f"{pref}{c1}{corner[0]}{c2}{(fill*length)[:filled]:{nullp}<{length}}{c1}{corner[1]}\033[0m{suff}"


def isbar(iteration, total, suff="", **kwargs):
    return f"{pbar(iteration, total, **kwargs)} {str(iteration).rjust(len(str(total)))}/{total} {suff}"


def ipbar(iterable, total=None, refresh_interval=0.25,
          end="\r", very_end="\n", clear=False, print_item=False, **kwargs):
    total = total or len(iterable)
    _time = time.time()
    for i, obj in enumerate(iterable):
        yield obj
        newtime = time.time()
        if newtime - _time > refresh_interval:  # refresh interval
            output = isbar(i+1, total, **kwargs)
            if print_item:
                output += f" {str(obj)}"
            print(f"\033[K{output}", end=end)
            _time = newtime
    print(isbar(total, total, **kwargs),
          end="\033[2K\r" if clear else very_end)


def thread_status(pid: int, item: str = "", extra: str = "", item_size=None):
    item_size = item_size or get_terminal_size().columns
    message = f"{pid}: {item}".ljust(
        item_size)[:item_size - len(extra)] + extra
    print(('\n' * pid) + message + ('\033[A' * pid), end="\r")


class Stepper:
    def __init__(self, step=0, print_mode="newline", print_class=print):
        self.print_modes = {
            "newline": ("", "\n"),
            "sameline": ("\033[2K", ""),
            "append": ("", "")
        }
        self.step = step
        self.print_mode = self.print_modes.get(print_mode)
        self.printer = print_class

    def next(self, s=None, **kwargs):
        self.step += 1
        if s:
            self._print(s, **kwargs)
        return self

    def print(self, *lines, **kwargs):
        for line in [f" {self.step}:{s}" for s in lines]:
            self._print(line, **kwargs)
        return self

    # override for print_modes
    def _print(self, *args, **kwargs):
        args = self.print_mode[0] + args[0], *args[1:]
        self.printer(*args, end=self.print_mode[1], **kwargs)


class RichStepper(Stepper):

    def __init__(self, loglevel=0, stepcolor="cyan", pstepcolor="blue", *args, **kwargs):
        from rich import print as rprint
        super().__init__(*args, **kwargs)
        self.printer = rprint
        self.loglevel = loglevel
        self.stepcolor = stepcolor
        self.pstepcolor = pstepcolor

    def set(self, n):
        self.step = n
        return self

    def next(self, s=None, **kwargs):
        self.step += 1
        if s:
            self._print(
                f"\n[{self.stepcolor}]{self.step}:[/{self.stepcolor}] {s}", **kwargs)
        else:
            self._print(
                f"\n[{self.stepcolor}]{self.step}:[/{self.stepcolor}]", **kwargs)
        return self

    def print(self, *lines, **kwargs):
        if isinstance(lines[0], int) or str(lines[0]).isdigit():
            level = int(lines[0])
            lines = lines[1:]
        else:
            level = 0
        printed_output = {
            0: "[bold yellow]INFO[/bold yellow]",
            1: "[bold orange]WARNING[/bold orange]",
            -1: "[bold grey]DEBUG[/bold grey]",
            2: "[bold red]ERROR[/bold red]",
            3: "[bold white]CRITICAL[/bold white]"
        }.get(level, f"[{self.pstepcolor}]{level}:[/{self.pstepcolor}]")
        output = [
            f" [{self.pstepcolor}]{self.step}:[/{self.pstepcolor}]" for _ in lines]
        if self.loglevel <= level:
            output = [f"{l} {printed_output}: " for i, l in enumerate(output)]
        output = [f"{output[i]} {s}" for i, s in enumerate(lines)]
        for line in output:
            self._print(line, **kwargs)
        return self


class Timer:
    def __init__(self, timestamp: int = None):
        self.time = timestamp or time.perf_counter()

    def print(self, msg):
        '''print and resets time'''
        return self.poll(msg).reset()

    def poll(self, msg=""):
        '''print without resetting time'''
        print(f"{time.perf_counter() - self.time}: {msg}")
        return self

    def reset(self):
        '''resets time'''
        self.time = time.perf_counter()
        return self.time

    def __repr__(self):
        return str((time.perf_counter()) - self.time)


if __name__ == "__main__":
    t = Timer()
    interval = 5_000
    for i in range(interval):
        time.time()
    t.print("time()")
    for i in range(interval):
        time.perf_counter()
    t.print("perf_counter()")
#     t = Timer()
    for i in range(100):
        for j in range(8):
            thread_status(j, t, extra=pbar(i, 100))
        time.sleep(0.01)
