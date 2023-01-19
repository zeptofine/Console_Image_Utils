from os import get_terminal_size
from time import perf_counter


def p_bar(iteration: int, total: int, length=20,
          fill="#", nullp="-", corner="[]", pref='', suff='') -> str:
    filledLength = (length * iteration) // total
    #    [#############################]
    return f"{str(pref)}\033[92m{corner[0]}\033[93m" + \
        (fill*length)[:filledLength] + (nullp*(length - filledLength)) + \
        f"\033[92m{corner[1]}\033[0m{str(suff)}"


def p_bar_stat(iteration, total, suff="", **kwargs):
    return f"{p_bar(iteration, total, **kwargs)} {iteration}/{total} {suff}"


def thread_status(pid: int, item: str = "", extra: str = "", item_size=None):
    item_size = item_size or get_terminal_size().columns
    message = f"{pid}: {item}".ljust(
        item_size)[:item_size - len(extra)] + extra
    print(('\n' * pid) + message + ('\033[A' * pid), end="\r")


class Stepper:
    def __init__(self, step=0, print_mode="newline", print_class=print):
        self.print_modes = {
            "newline": ("", "\n"),
            "sameline": ("\033[A", ""),
            "append": ("", "")
        }
        self.step = step
        self.print_mode = self.print_modes.get(print_mode)
        self.printer = print_class

    def next(self, s=None, **kwargs):
        self.step += 1
        if s:
            self.printer(f"{self.print_mode[0]}{self.step}: {s}",
                         end=self.print_mode[1], **kwargs)

    def print(self, *lines, **kwargs):
        for line in [f" {self.step}:{s}" for s in lines]:
            self.printer(line, **kwargs)
            # self.printer(
            #     f"{self.print_mode[0]}{line}", end=self.print_mode[1], **kwargs)

    # override for print_modes
    def _print(self, *args, **kwargs):
        args = self.print_mode[0] + args[0], *args[1:]
        self.printer(*args, end=self.print_mode[1], **kwargs)

class RichStepper(Stepper):

    def __init__(self, loglevel=0, *args, **kwargs):
        from rich import print as rprint
        super().__init__(*args, **kwargs)
        self.printer = rprint
        self.loglevel = loglevel

    def set(self, n):
        self.step = n
        return self

    def next(self, s=None, **kwargs):
        self.step += 1
        if s:
            self._print(f"[green]{self.step}:[/green] {s}", **kwargs)

    def print(self, *lines, **kwargs):
        if isinstance(lines[0], int) or lines[0].isdigit():
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
        }.get(level, f"[blue]{level}[/blue]")
        output = [f" [blue]{self.step}:[/blue]" for _ in lines]
        if self.loglevel <= level:
            output = [f"{l} {printed_output}: " for i, l in enumerate(output)]
        output = [f"{output[i]} {s}" for i,s in enumerate(lines)]
        for line in output:
            self._print(line, **kwargs)


class Timer:
    def __init__(self, timestamp: int = None):
        self.time = timestamp or perf_counter()

    def print(self, msg):
        '''print and resets time'''
        return self.poll(msg).reset()

    def poll(self, msg=""):
        '''print without resetting time'''
        print(f"{perf_counter() - self.time}: {msg}")
        return self

    def reset(self):
        '''resets time'''
        self.time = perf_counter()
        return self.time

    def __repr__(self):
        return str((perf_counter()) - self.time)


# if __name__ == "__main__":
#     t = Timer()
#     for i in range(100):
#         for j in range(8):
#             thread_status(j, t, extra=p_bar(i, 100))
