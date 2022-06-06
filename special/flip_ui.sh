#!/bin/bash
# if argument is gui, then startup the gui
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-$0}")" &>/dev/null && pwd 2>/dev/null)"
if [ ! "$#" -eq 0 ]; then
    if [ "$1" == "--init" ]; then
        cp -f "$SCRIPT_DIR/flip_ui.sh" ~/.flip.ui.sh
        echo "Copied flip_ui.sh to ~/.flip.ui.sh"
        read -r -n 1 -p "write to ~/.zshrc? [Y/n]" response
        if [ "${response:=y}" == "y" ]; then
            echo "source ~/.flip.ui.sh" >>~/.zshrc
            echo "Added source ~/.flip.ui.sh to ~/.zshrc"
        fi
        read -r -n 1 -p "write to ~/.bashrc? [Y/n]" response
        if [ "${response:=y}" == "y" ]; then
            echo "source ~/.flip.ui.sh" >>~/.bashrc
            echo "Added source ~/.flip.ui.sh to ~/.bashrc"
        fi
        echo "source ~/.flip.ui.sh to get the commands now, or restart your terminal"
    fi
fi
function flip_gui {
    systemctl isolate graphical.target
}
function flip_cli {
    systemctl isolate multi-user.target
}