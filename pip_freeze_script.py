try:
    from rich import print as rprint
except:
    from pprint import pprint as rprint
import subprocess

# This was made for reference for future projects.
def getPackages(pip='pip'):
    '''Gets every package available to a given python installation.
        Use a table for the pip argument if it contains multiple commands.'''
    command = [pip]
    if isinstance(pip, list): command = pip 
    command.append('freeze')
    x0 = subprocess.check_output(command).decode('UTF-8').split()
    x1 = [i.split("==") if "==" in i else [i, None] for i in x0]
    x2 = {i[0]: i[1] for i in x1}
    return x2


if __name__ == "__main__":
    packages = getPackages()
    rprint(packages)
    rprint(f"{len(packages.keys())} individual packages")
