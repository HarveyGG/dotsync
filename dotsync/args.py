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
                            help='encrypt the file (for add command)')

        parser.add_argument('action', choices=[a.value for a in Actions],
                            help=HELP['action'])
        # For 'add' action: category[0] is filepath, category[1] is optional category name
        # For 'encrypt' action: category[0] is filepath
        # For 'unmanage' action: category[0] is filepath
        # For other actions: category is list of category names
        category_help = HELP['category']
        add_help = 'filepath [category] - add new config file to filelist'
        encrypt_help = 'filepath - convert existing config file to encrypted'
        unmanage_help = 'filepath - restore file to home and stop managing it'
        
        # For init: category[0] is optional directory path (defaults to ~/.dotfiles)
        init_help = '[directory] - initialize dotsync repository (default: ~/.dotfiles)'
        category_help_extended = f'{category_help} (for "init": {init_help}, for "add": {add_help}, for "encrypt": {encrypt_help}, for "unmanage": {unmanage_help})'
        
        parser.add_argument('category', nargs='*',
                            default=['common', info.hostname],
                            help=category_help_extended)

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
        # For add action, category[0] is filepath, category[1] is category name
        elif args.action == 'add':
            if len(args.category) < 1:
                parser.error('add action requires at least one argument: filepath [category]')
            self.add_filepath = args.category[0]
            self.add_category = args.category[1] if len(args.category) > 1 else None
        # For encrypt action, category[0] is filepath
        elif args.action == 'encrypt':
            if len(args.category) < 1:
                parser.error('encrypt action requires filepath argument')
            self.add_filepath = args.category[0]
            self.add_category = None
        # For unmanage action, category[0] is filepath
        elif args.action == 'unmanage':
            if len(args.category) < 1:
                parser.error('unmanage action requires filepath argument')
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
        self.action = Actions(args.action)
        self.categories = args.category

    def __str__(self):
        return str(vars(self))
