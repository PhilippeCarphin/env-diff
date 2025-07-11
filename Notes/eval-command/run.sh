bad(){
    #source arg-printer.sh asdf
    (
        if ! eval "$@" ; then
            echo "error"
        fi
    )
}

good(){
    (
        the_cmd=("$@")
        set --
        eval "${the_cmd[@]}"
    )
}

echo ============= expectation ====================
cmd=(source ./arg-printer.sh arg-to-sourced-script)
echo "running '${cmd[*]}'"
"${cmd[@]}"
echo ""

cmd=(source ./arg-printer.sh)
echo "running '${cmd[*]}'"
"${cmd[@]}"
echo ""

echo ============= bad ====================
cmd=(bad source ./arg-printer.sh arg-to-sourced-script)
echo "running '${cmd[*]}'"
"${cmd[@]}"
echo ""

cmd=(bad source ./arg-printer.sh)
echo "running '${cmd[*]}'"
"${cmd[@]}"
echo ""

echo ============= good ====================
cmd=(good source ./arg-printer.sh arg-to-sourced-script)
echo "running '${cmd[*]}'"
"${cmd[@]}"
echo ""

cmd=(good source ./arg-printer.sh)
echo "running '${cmd[*]}'"
"${cmd[@]}"
