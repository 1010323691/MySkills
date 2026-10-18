# BEGIN Claude workbench integration
# Manual integration is needed because Ghostty launches a tmux entry script.
if [[ $- == *i* && -n ${GHOSTTY_RESOURCES_DIR:-} && -r "$GHOSTTY_RESOURCES_DIR/shell-integration/bash/ghostty.bash" ]] && ! declare -F __ghostty_hook >/dev/null; then
    export GHOSTTY_SHELL_FEATURES="${GHOSTTY_SHELL_FEATURES:-cursor,title}"
    export GHOSTTY_BIN_DIR="${GHOSTTY_BIN_DIR:-/usr/bin}"
    builtin source "$GHOSTTY_RESOURCES_DIR/shell-integration/bash/ghostty.bash"
fi
# END Claude workbench integration
