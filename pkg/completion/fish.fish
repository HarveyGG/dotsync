# completion for dotsync
# original author @ncoif

function __fish_dotsync_no_subcommand -d 'Test if dotsync has yet to be given the subcommand'
	for i in (commandline -opc)
		if contains -- $i init update restore clean diff commit passwd
			return 1
		end
	end
	return 0
end

complete -f -n '__fish_dotsync_no_subcommand' -c dotsync -a 'init' -d 'Setup a new dotsync repository'
complete -f -n '__fish_dotsync_no_subcommand' -c dotsync -a 'update' -d 'Update the repository structure to match filelists'
complete -f -n '__fish_dotsync_no_subcommand' -c dotsync -a 'restore' -d 'Create links from the home folder to the repository'
complete -f -n '__fish_dotsync_no_subcommand' -c dotsync -a 'clean' -d 'Remove links in the home folder'
complete -f -n '__fish_dotsync_no_subcommand' -c dotsync -a 'diff' -d 'Print the current changes'
complete -f -n '__fish_dotsync_no_subcommand' -c dotsync -a 'commit' -d 'Generate a commit and push the changes'
complete -f -n '__fish_dotsync_no_subcommand' -c dotsync -a 'passwd' -d 'Change the dotsync encryption password'
