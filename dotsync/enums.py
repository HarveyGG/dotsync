import enum


class Actions(enum.Enum):
    """Actions ordered by typical usage lifecycle"""
    INIT = 'init'          # Initialize dotsync repository (first-time setup)
    TRACK = 'track'        # Add config file to filelist (bootstrap repo if missing)
    UNTRACK = 'untrack'    # Restore file to home and stop managing it
    ADD = 'add'            # Deprecated alias for track
    ENCRYPT = 'encrypt'    # Convert existing plain config to encrypted
    UNMANAGE = 'unmanage'  # Deprecated alias for untrack
    LIST = 'list'          # List all managed configuration files
    CATEGORIES = 'categories'  # Show category groups and definitions
    UPDATE = 'update'      # Sync config files from home to repository
    SAVE = 'save'          # Mirror home to repo, commit, and push
    RESTORE = 'restore'    # Restore config files from repository to home
    DIFF = 'diff'          # Show differences between home and repository
    COMMIT = 'commit'      # Commit changes to git and optionally push
    CLEAN = 'clean'        # Remove files from repository that are no longer managed
    PASSWD = 'passwd'      # Change encryption password for encrypted files
    SHOWPW = 'showpw'      # Print stored encryption password (local machine only)
