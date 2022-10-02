try:
    from rich import print as rprint
except ImportError:
    rprint = print


def pBar(iteration: int, total: int, length=10,
         fill="#", nullp="-", corner="[]", pref='', suff=''):
    color1, color2 = (
        "\033[93m", "\033[92m")
    filledLength = (length * iteration) // total
    #    [############################# --------------------------------]
    bar = (fill*length)[:filledLength] + (nullp*(length - filledLength))
    command = f"{color2}{corner[0]}{color1}{bar}{color2}{corner[1]}\033[0m"
    command = str(pref)+command+str(suff)
    return command


def threadStatus(pid, item="", extra="", anonymous=False, extraSize=8):
    output = f"\033[K {str(pid).ljust(3)} | {str(extra).center(extraSize)}"
    if not anonymous:
        output += f" | {item}"
    else:
        output += " | ..."
    output = ('\n'*pid) + output + ('\033[A'*pid)
    print(output, end="\r")


def nextStep(order, text):
    rprint(" "+f"{str(order)}. {text}", end="\n\033[K")


class numFmt:

    class Bit:
        def __init__(self, amount):
            self.amount = amount
            # * IEC
            self.kibibits = self.lvl_iec_up(self.amount)
            self.mebibits = self.lvl_iec_up(self.kibibits)
            self.gibibits = self.lvl_iec_up(self.mebibits)
            self.tebibits = self.lvl_iec_up(self.gibibits)
            self.pebibits = self.lvl_iec_up(self.tebibits)
            self.exbibits = self.lvl_iec_up(self.pebibits)
            self.zebibits = self.lvl_iec_up(self.exbibits)
            self.yobibits = self.lvl_iec_up(self.zebibits)
            # * Metric
            self.kilobits = self.lvl_metric_up(self.amount)
            self.megabits = self.lvl_metric_up(self.kilobits)
            self.gigabits = self.lvl_metric_up(self.megabits)
            self.terabits = self.lvl_metric_up(self.gigabits)
            self.petabits = self.lvl_metric_up(self.terabits)
            self.exabits = self.lvl_metric_up(self.petabits)
            self.zettabits = self.lvl_metric_up(self.exabits)
            self.yottabits = self.lvl_metric_up(self.zettabits)

        def lvl_iec_up(self, amount):
            return amount / (2**10)

        def lvl_metric_up(self, amount):
            return amount / (10**3)

        def fmt_iec(self) -> tuple:
            for fmt in reversed([(self.amount, "bit"), (self.kibibits, "Kibit"),
                                 (self.mebibits, "Mibit"), (self.gibibits, "Gibit"),
                                 (self.tebibits, "Tibit"), (self.pebibits, "Pibit"),
                                 (self.exbibits, "Eibit"), (self.zebibits, "Zibit"),
                                 (self.yobibits, "Yibit")]):
                if (fmt[0] >= 1):
                    return fmt
            return (-1, "NaN")

        def fmt_metric(self) -> tuple:
            for fmt in reversed([(self.amount, "bit"), (self.kilobits, "kbit"),
                                 (self.megabits, "Mbit"), (self.gigabits, "Gbit"),
                                 (self.terabits, "Tbit"), (self.petabits, "Pbit"),
                                 (self.exabits, "Ebit"), (self.zettabits, "Zbit"),
                                 (self.yottabits, "Ybit")]):
                if (fmt[0] >= 1):
                    return fmt
            return (-1, "NaN")

        def to_bytes(self):
            return numFmt.Byte(self.amount / 8)

        def __str__(self):
            return str(self.amount)

        def dict(self):
            return self.__dict__

    class Byte:
        def __init__(self, amount):
            self.amount = amount
            # * IEC
            self.kibibytes = self.lvl_iec_up(self.amount)
            self.mebibytes = self.lvl_iec_up(self.kibibytes)
            self.gibibytes = self.lvl_iec_up(self.mebibytes)
            self.tebibytes = self.lvl_iec_up(self.gibibytes)
            self.pebibytes = self.lvl_iec_up(self.tebibytes)
            self.exbibytes = self.lvl_iec_up(self.pebibytes)
            self.zebibytes = self.lvl_iec_up(self.exbibytes)
            self.yobibytes = self.lvl_iec_up(self.zebibytes)
            # * Metric
            self.kilobytes = self.lvl_metric_up(self.amount)
            self.megabytes = self.lvl_metric_up(self.kilobytes)
            self.gigabytes = self.lvl_metric_up(self.megabytes)
            self.terabytes = self.lvl_metric_up(self.gigabytes)
            self.petabytes = self.lvl_metric_up(self.terabytes)
            self.exabytes = self.lvl_metric_up(self.petabytes)
            self.zettabytes = self.lvl_metric_up(self.exabytes)
            self.yottabyte = self.lvl_metric_up(self.zettabytes)

        def lvl_iec_up(self, amount):
            return amount / (2**10)

        def lvl_metric_up(self, amount):
            return amount / (10**3)

        def fmt_iec(self) -> tuple:
            for fmt in reversed([(self.amount, "B"), (self.kibibytes, "KiB"),
                                 (self.mebibytes, "MiB"), (self.gibibytes, "GiB"),
                                 (self.tebibytes, "TiB"), (self.pebibytes, "PiB"),
                                 (self.exbibytes, "EiB"), (self.zebibytes, "ZiB"),
                                 (self.yobibytes, "YiB")]):
                if (fmt[0] >= 1):
                    return fmt
            return (-1, "NaN")

        def fmt_metric(self) -> tuple:
            for fmt in reversed([(self.amount, "B"), (self.kilobytes, "kB"),
                                 (self.megabytes, "MB"), (self.gigabytes, "GB"),
                                 (self.terabytes, "TB"), (self.petabytes, "PB"),
                                 (self.exabytes, "EB"), (self.zettabytes, "ZB"),
                                 (self.yottabyte, "YB")]):
                if (fmt[0] >= 1):
                    return fmt
            return (-1, "NaN")

        def __str__(self):
            return str(self.amount)

        def to_bits(self):
            return numFmt.Bit(self.amount * 8)

        def dict(self):
            return self.__dict__


if __name__ == "__main__":
    machinesize = numFmt.Bit(1000000)
    machinesizeByte = machinesize.to_bytes()
    print(machinesize.dict())
    print(machinesizeByte.dict())
    # rprint(machinesize.lvl_deci_up(machinesize.amount))
    print(machinesize)
    print(machinesize.fmt_metric())
    print(machinesize.fmt_iec())
    print(machinesizeByte.fmt_metric())
    print(machinesizeByte.fmt_iec())
