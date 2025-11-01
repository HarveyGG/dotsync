import enum


class Actions(enum.Enum):
    """Actions ordered by typical usage lifecycle"""
    INIT = 'init'          # Initialize dotsync repository (first-time setup)
    ADD = 'add'            # Add new config file to filelist
    ENCRYPT = 'encrypt'    # Convert existing plain config to encrypted
    UNMANAGE = 'unmanage'  # Restore file to home and stop managing it
    LIST = 'list'          # List all managed configuration files
    UPDATE = 'update'      # Sync config files from home to repository
    RESTORE = 'restore'    # Restore config files from repository to home
    DIFF = 'diff'          # Show differences between home and repository
    COMMIT = 'commit'      # Commit changes to git and optionally push
    CLEAN = 'clean'        # Remove files from repository that are no longer managed
    PASSWD = 'passwd'      # Change encryption password for encrypted files
