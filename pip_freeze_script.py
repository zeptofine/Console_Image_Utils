from pprint import pprint
import subprocess


def getPackages(pip='pip'):
    x0 = subprocess.check_output([pip, 'freeze']).decode('UTF-8').split()
    x1 = [i.split("==") if "==" in i else [i, ""] for i in x0]
    x2 = {i[0]: i[1] for i in x1}
    return x2


if __name__ == "__main__":
    packages = getPackages()
    pprint(packages)
    pprint(f"{len(packages.keys())} individual packages")
