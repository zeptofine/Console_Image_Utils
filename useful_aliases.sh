#!/bin/bash

# opens the zshrc in `micro` and reloads oh-my-zsh.
alias zshconfig="micro ~/.zshrc; omz reload"

alias restart-plasma="systemctl --user restart plasma-plasmashell.service"
alias restart-x11="systemctl --user restart plasma-kwin_x11.service"

# clears the cache. I use this when checking performance without the help of caching.
alias clear-cache="sudo sysctl vm.drop_caches=3"

# sets up a python virtualenv in .venv. Ignore folder not found errors.
alias setupenv="rm -r .venv; python -m virtualenv --clear --download .venv; cd ./; python -m ensurepip; python -m pip install --upgrade pip"

# taken from https://stackoverflow.com/a/17647645. Very useful sometimes!
alias find-exts="find . -type f | grep -oE '\.(\w+)$' | sort -u"

alias lsar="ls -lahR"

alias open="xdg-open"
