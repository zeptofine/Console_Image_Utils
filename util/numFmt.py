class numFmt:
    # '''classes of bits and bytes to assist conversion'''
    class Bit:
        #     '''Bits to assist conversion between:
        #         - metric (MBit, etc.),
        #         - iec (Mibit, etc.)'''
        def __init__(self, amount):
            self.amount = amount
            # * IEC
            self.iec = ['bit', 'Kibit', 'Mibit',
                        'Gibit', 'Tibit', 'Pibit',
                        'Eibit', 'Zibit', 'Yibit']
            # * Metric
            self.metric = ['bit', 'kbit', 'Mbit',
                           'Gbit', 'Tbit', 'Pbit',
                           'Ebit', 'Zbit', 'Ybit']

        def fmt_iec(self) -> tuple:
            for count, fmt in enumerate(self.iec):
                num = self.amount / (2**10)**count
                if (num <= (2**10) and (num >= 1)):
                    return (num, fmt)
            return (-1, "NaN")

        def fmt_metric(self) -> tuple:
            for count,  fmt in enumerate(self.metric):
                num = self.amount / (10**3)**count
                if (num < (10**3)) and (num >= 1):
                    return (num, fmt)
            return (-1, "NaN")

        def to_bytes(self):
            return numFmt.Byte(self.amount / 8)

        def __str__(self):
            return str(self.amount)

        def dict(self):
            return self.__dict__

    class Byte:
        '''Bytes to assist conversion between:
            - metric (MB, etc.),
            - iec (Mib, etc.)'''

        def __init__(self, amount):
            self.amount = amount
            # * IEC
            self.iec = ['B', 'KiB', 'MiB',
                        'GiB', 'TiB', 'PiB',
                        'EiB', 'ZiB', 'YiB']
            # * Metric
            self.metric = ['B', 'kB', 'MB',
                           'GB', 'TB', 'PB',
                           'EB', 'ZB', 'YB']

        def fmt_iec(self) -> tuple:
            for count, fmt in enumerate(self.iec):
                num = self.amount / (2**10)**count
                if (num <= (2**10) and (num >= 1)):
                    return (num, fmt)
            return (-1, "NaN")

        def fmt_metric(self) -> tuple:
            for count, fmt in enumerate(self.metric):
                num = self.amount / (10**3)**count
                if (num < (10**3)) and (num >= 1):
                    return (num, fmt)
            return (-1, "NaN")

        def __str__(self):
            return str(self.amount)

        def to_bits(self):
            return numFmt.Bit(self.amount * 8)

        def dict(self):
            return self.__dict__
