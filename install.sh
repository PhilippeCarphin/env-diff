#!/bin/bash
this_dir=$(cd -P $(dirname $0) && pwd)
echo "Add \`source $this_dir/env-diff-cmd.bash\` in your ~/.bashrc"
echo "You can also \`cp dot-config-env-diff-cmd.yml $HOME/.config/env-diff.yml\`"
