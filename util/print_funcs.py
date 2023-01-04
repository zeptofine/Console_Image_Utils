import time


def p_bar(iteration: int, total: int, length=20,
          fill="#", nullp="-", corner="[]", pref='', suff='') -> str:
    filledLength = (length * iteration) // total
    #    [#############################]
    return f"{str(pref)}\033[92m{corner[0]}\033[93m" + \
            (fill*length)[:filledLength] + (nullp*(length - filledLength)) + \
            f"\033[92m{corner[1]}\033[0m{str(suff)}"

def thread_status(pid: int, item: str = "", extra: str = "", item_size = None):
    item_size = item_size or os.get_terminal_size().columns
    message = f"{pid}: {item}"
    message = message[:item_size - len(extra) - 2] + extra
    message += " " * (item_size - len(message))
    print(f"{'\n' * pid}{message}{'\033[A' * pid}", end="\r")

class Timer:
    def __init__(self, timestamp: int = None):
        self.time = timestamp or time.perf_counter()

    def print(self, msg):
        '''print and resets time'''
        return self.poll(msg).reset()

    def poll(self, msg):
        '''print without resetting time'''
        print(f"{time.perf_counter() - self.time}: {msg}")
        return self

    def reset(self):
        '''resets time'''
        self.time = time.perf_counter()
        return self.time

    def __repr__(self):
        output = str((newtime := time.perf_counter()) - self.time)
        self.time = newtime
        return output

