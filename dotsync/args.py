import logging
import argparse
import os

from dotsync.enums import Actions
import dotsync.info as info

HELP = {
    'verbose': 'increase verbosity level',
    'dry-run': 'do not actually execute any file operations',
    'hard-mode': 'copy files instead of symlinking them',
    'action': 'action to take on active categories',
    'category': 'categories to activate (default: common + hostname)'
}

EPILOG = 'See full the documentation at https://dotsync.readthedocs.io/'


class CustomHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom formatter that hides default values containing hostname"""
    def _get_help_string(self, action):
        help_text = action.help
        # Replace %(default)s placeholder
        if '%(default)s' in help_text:
            if action.dest == 'category':
                default = action.default
                if isinstance(default, list) and len(default) == 2 and default[1] == info.hostname:
                    help_text = help_text.replace('%(default)s', 'common + hostname')
                else:
                    help_text = help_text % {'default': default}
            else:
                help_text = help_text % {'default': action.default}
        return help_text
    
    def _format_action(self, action):
        """Override to hide default display for category argument"""
        # Temporarily remove default to prevent argparse from showing it
        if action.dest == 'category' and hasattr(action, 'default'):
            original_default = action.default
            # Replace with SUPPRESS to hide it from help output
            action.default = argparse.SUPPRESS
        
        # Format the action
        result = super()._format_action(action)
        
        # Restore original default
        if action.dest == 'category' and 'original_default' in locals():
            action.default = original_default
        
        return result


class Arguments:
    def __init__(self, args=None):
        # construct parser
        parser = argparse.ArgumentParser(prog='dotsync',
                                         epilog=EPILOG,
                                         formatter_class=CustomHelpFormatter)

        # add parser options
        parser.add_argument('--version', action='version',
                            version=f'dotsync {info.__version__}')
        parser.add_argument('--verbose', '-v', action='count', default=0,
                            help=HELP['verbose'])
        parser.add_argument('--dry-run', action='store_true',
                            help=HELP['dry-run'])
        parser.add_argument('--hard', action='store_true',
                            help=HELP['hard-mode'])
        parser.add_argument('--encrypt', action='store_true',
                            help='encrypt the file (for track command)')
        parser.add_argument('--purge-repo', action='store_true',
                            help='remove mirrored files from repository when untracking')
        parser.add_argument('--non-interactive', action='store_true',
                            help='skip prompts, use policy defaults')
        parser.add_argument('--yes', '-y', action='store_true',
                            help='non-interactive mode; skip confirmation prompts')
        parser.add_argument('--remote', default=None,
                            help='Git remote URL for restore wizard (new machine)')
        parser.add_argument('--categories', dest='categories_filter', default=None,
                            help='comma-separated categories for restore')

        parser.add_argument('action', choices=[a.value for a in Actions],
                            help=HELP['action'])
        # For 'track'/'add': category[0] is filepath, category[1] is optional category name
        # For 'encrypt' action: category[0] is filepath
        # For 'untrack'/'unmanage': category[0] is filepath
        # For other actions: category is list of category names
        category_help = HELP['category']
        track_help = 'filepath [category] - add config file to filelist'
        encrypt_help = 'filepath - convert existing config file to encrypted'
        untrack_help = 'filepath - restore file to home and stop managing it'
        
        # For init: category[0] is optional directory path (defaults to ~/.dotfiles)
        init_help = '[directory] - initialize dotsync repository (default: ~/.dotfiles)'
        category_help_extended = (
            f'{category_help} (for "init": {init_help}, for "track": {track_help}, '
            f'for "encrypt": {encrypt_help}, for "untrack": {untrack_help})'
        )
        
        parser.add_argument('category', nargs='*',
                            default=['common', info.hostname],
                            help=category_help_extended)
        parser.add_argument('--conflict', choices=['prompt', 'overwrite', 'keep', 'abort'],
                            default='prompt',
                            help='conflict resolution when non-interactive')
        parser.add_argument('--candidate', choices=['prompt', 'prefer-home', 'prefer-master', 'abort'],
                            default='prompt',
                            help='candidate selection when multiple versions exist')
        parser.add_argument('--keep-going', action='store_true',
                            help='continue on file errors, report at end')
        parser.add_argument('--no-auto-update', action='store_true',
                            help='skip auto-update after add (for large dirs)')
        parser.add_argument('--skip-pull', action='store_true',
                            help='skip git pull before restore (unsafe)')
        parser.add_argument('--no-push', action='store_true',
                            help='commit locally but do not push to remote')
        parser.add_argument('-m', '--message', dest='commit_message',
                            default=None,
                            help='commit message for save command')

        # parse args
        args = parser.parse_args(args)
        
        # For init action, category[0] is optional directory path
        if args.action == 'init':
            # Check if user provided a directory (not the default categories)
            # Default is ['common', info.hostname], so if category doesn't match this pattern, it's a directory
            if len(args.category) > 0:
                # If category looks like a path (contains / or starts with ~ or is absolute), it's a directory
                first_arg = args.category[0]
                if ('/' in first_arg or first_arg.startswith('~') or os.path.isabs(first_arg) or 
                    first_arg not in ['common']):
                    # User provided a directory
                    self.init_directory = first_arg
                else:
                    # Probably default categories, use default directory
                    self.init_directory = None
            else:
                # No arguments, use default directory
                self.init_directory = None
        # For track/add, category[0] is filepath, category[1] is category name
        elif args.action in ('track', 'add'):
            if len(args.category) < 1:
                parser.error('track action requires at least one argument: filepath [category]')
            self.add_filepath = args.category[0]
            self.add_category = args.category[1] if len(args.category) > 1 else None
        # For encrypt action, category[0] is filepath
        elif args.action == 'encrypt':
            if len(args.category) < 1:
                parser.error('encrypt action requires filepath argument')
            self.add_filepath = args.category[0]
            self.add_category = None
        # For untrack/unmanage, category[0] is filepath
        elif args.action in ('untrack', 'unmanage'):
            if len(args.category) < 1:
                parser.error('untrack action requires filepath argument')
            self.add_filepath = args.category[0]
            self.add_category = None
        else:
            self.add_filepath = None
            self.add_category = None
            self.init_directory = None

        # extract settings
        if args.verbose:
            args.verbose = min(args.verbose, 2)
            self.verbose_level = (logging.INFO if args.verbose < 2 else
                                  logging.DEBUG)
        else:
            self.verbose_level = logging.WARNING

        self.dry_run = args.dry_run
        self.hard_mode = args.hard
        self.encrypt = getattr(args, 'encrypt', False)
        self.non_interactive = getattr(args, 'non_interactive', False)
        self.yes = getattr(args, 'yes', False)
        if self.yes:
            self.non_interactive = True
        self.remote = getattr(args, 'remote', None)
        self.categories_filter = getattr(args, 'categories_filter', None)
        self.conflict = getattr(args, 'conflict', 'prompt')
        self.candidate = getattr(args, 'candidate', 'prompt')
        self.keep_going = getattr(args, 'keep_going', False)
        self.no_auto_update = getattr(args, 'no_auto_update', False)
        self.skip_pull = getattr(args, 'skip_pull', False)
        self.no_push = getattr(args, 'no_push', False)
        self.commit_message = getattr(args, 'commit_message', None)
        self.purge_repo = getattr(args, 'purge_repo', False)
        self.action = Actions(args.action)
        self.categories = args.category
        if self.categories_filter:
            self.categories = [
                c.strip() for c in self.categories_filter.split(',') if c.strip()
            ]

    def __str__(self):
        return str(vars(self))
