# Interactive Bash only. Existing CUDA/environment setup stays in ~/.bashrc.
[[ $- == *i* ]] || return
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) export PATH="$HOME/.local/bin:$PATH" ;;
esac
[[ -r "$HOME/.config/terminal-workbench/colors.bash" ]] && source "$HOME/.config/terminal-workbench/colors.bash"
export EDITOR=micro
export VISUAL=micro
export COLORTERM=truecolor
# The installed system tool remains available independently of desktop apps.
alias rg='/usr/bin/rg'
alias fd='fdfind'
alias bat='batcat'
alias ll='eza -lah --icons=auto --group-directories-first'
alias lt='eza --tree --level=2 --icons=auto --group-directories-first'
alias ff='terminal-files'
alias proj='terminal-project'
export FZF_DEFAULT_COMMAND='fdfind --type f --hidden --exclude .git'
export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
export FZF_ALT_C_COMMAND='fdfind --type d --hidden --exclude .git'
export FZF_CTRL_T_OPTS='--preview="batcat --color=always --style=numbers --line-range=:160 -- {} 2>/dev/null" --preview-window=right:55%:wrap'
# Avoid repeatedly registering hooks when .bashrc is sourced.
if [[ ${__workbench_fzf_ready:-} != 1 ]]; then
    eval "$(fzf --bash)"
    __workbench_fzf_ready=1
fi
if [[ ${__workbench_zoxide_ready:-} != 1 ]]; then
    eval "$(zoxide init bash)"
    __workbench_zoxide_ready=1
fi
if [[ ${__workbench_starship_ready:-} != 1 && $TERM != dumb ]]; then
    eval "$(starship init bash)"
    __workbench_starship_ready=1
fi
# Starship preserves earlier prompt hooks but runs them before building PS1.
# Ghostty must mark the completed Starship prompt, so run it afterwards.
if declare -F __ghostty_hook >/dev/null && [[ ${__workbench_starship_ready:-} == 1 ]]; then
    STARSHIP_PROMPT_COMMAND=${STARSHIP_PROMPT_COMMAND//__ghostty_hook/}
    if [[ " ${PROMPT_COMMAND[*]} " != *' __ghostty_hook '* ]]; then
        PROMPT_COMMAND+=(__ghostty_hook)
    fi
fi
