import os
from distutils.dir_util import copy_tree

cp_from = input("Folder to copy: ")
cp_to = input("Folder to copy to: ")

copy_tree(cp_from, cp_to)