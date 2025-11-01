#!/usr/bin/env python3
"""
Test diff and commit commands
"""
import sys
import os
import tempfile
import subprocess

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotsync.__main__ import main
from dotsync.git import Git

def test_diff():
    """Test diff command"""
    print("Testing 'diff' command...")
    with tempfile.TemporaryDirectory() as tmpdir:
        home = os.path.join(tmpdir, 'home')
        repo = os.path.join(tmpdir, 'repo')
        os.makedirs(home)
        os.makedirs(repo)
        
        # Init
        main(args=['init'], cwd=repo, home=home)
        
        # Add a file
        test_file = os.path.join(home, '.testfile')
        with open(test_file, 'w') as f:
            f.write('test')
        
        main(args=['add', '.testfile'], cwd=repo, home=home)
        main(args=['update'], cwd=repo, home=home)
        
        # Modify file
        with open(test_file, 'w') as f:
            f.write('modified')
        
        # Test diff
        result = main(args=['diff'], cwd=repo, home=home)
        assert result == 0, f"diff failed with code {result}"
        print("✓ diff command works")

def test_commit():
    """Test commit command"""
    print("Testing 'commit' command...")
    with tempfile.TemporaryDirectory() as tmpdir:
        home = os.path.join(tmpdir, 'home')
        repo = os.path.join(tmpdir, 'repo')
        os.makedirs(home)
        os.makedirs(repo)
        
        # Set up git user (required for commit)
        subprocess.run(['git', 'config', '--global', 'user.name', 'Test User'], 
                      capture_output=True)
        subprocess.run(['git', 'config', '--global', 'user.email', 'test@example.com'], 
                      capture_output=True)
        
        # Init
        main(args=['init'], cwd=repo, home=home)
        
        # Add a file
        test_file = os.path.join(home, '.testfile')
        with open(test_file, 'w') as f:
            f.write('test')
        
        main(args=['add', '.testfile'], cwd=repo, home=home)
        main(args=['update'], cwd=repo, home=home)
        
        # Modify the file to create a change
        with open(test_file, 'w') as f:
            f.write('modified')
        main(args=['update'], cwd=repo, home=home)
        
        # Test commit
        result = main(args=['commit'], cwd=repo, home=home)
        assert result == 0, f"commit failed with code {result}"
        
        # Verify commit was created (commit message should contain something)
        git = Git(repo)
        last_commit = git.last_commit()
        assert len(last_commit) > 0, "Commit message should not be empty"
        print("✓ commit command works")

def test_commit_no_changes():
    """Test commit when there are no changes"""
    print("Testing 'commit' with no changes...")
    with tempfile.TemporaryDirectory() as tmpdir:
        home = os.path.join(tmpdir, 'home')
        repo = os.path.join(tmpdir, 'repo')
        os.makedirs(home)
        os.makedirs(repo)
        
        # Init
        main(args=['init'], cwd=repo, home=home)
        
        # Test commit with no changes
        result = main(args=['commit'], cwd=repo, home=home)
        assert result == 0, "commit should handle no changes gracefully"
        print("✓ commit handles no changes correctly")

if __name__ == '__main__':
    print("=" * 60)
    print("Testing diff and commit commands...")
    print("=" * 60)
    
    try:
        test_diff()
        test_commit_no_changes()
        test_commit()
        print("=" * 60)
        print("All diff and commit tests passed!")
        print("=" * 60)
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

