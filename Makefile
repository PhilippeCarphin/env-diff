# I'm going to version the generated env-diff.1 file so it's not going
# to be a dependency of 'install' since not everybody has pandoc or emacs.
man: env-diff.1 env-diff-gencode.1 env-diff-load.1 env-diff-save.1
%.1:%.org
	pandoc -s -f org -t man -o $@ $^ || \
	( emacs --batch -l ox-man $^ -f org-man-export-to-man && mv env-diff.man env-diff.1 )
