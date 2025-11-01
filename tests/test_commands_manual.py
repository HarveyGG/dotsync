#!/usr/bin/env python3
"""
Manual test script for dotsync commands
Run with: python3 test_commands_manual.py
"""
import sys
import os
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotsync.__main__ import main

def test_init():
    """Test init command"""
    print("Testing 'init' command...")
    with tempfile.TemporaryDirectory() as tmpdir:
        home = os.path.join(tmpdir, 'home')
        repo = os.path.join(tmpdir, 'repo')
        os.makedirs(home)
        os.makedirs(repo)
        
        result = main(args=['init'], cwd=repo, home=home)
        assert result == 0, f"init failed with code {result}"
        assert os.path.exists(os.path.join(repo, 'filelist')), "filelist not created"
        assert os.path.exists(os.path.join(repo, '.git')), "git repo not created"
        print("✓ init command works")

def test_add():
    """Test add command"""
    print("Testing 'add' command...")
    with tempfile.TemporaryDirectory() as tmpdir:
        home = os.path.join(tmpdir, 'home')
        repo = os.path.join(tmpdir, 'repo')
        os.makedirs(home)
        os.makedirs(repo)
        
        # Init first
        main(args=['init'], cwd=repo, home=home)
        
        # Create test file
        test_file = os.path.join(home, '.testfile')
        with open(test_file, 'w') as f:
            f.write('test')
        
        # Test add with auto category
        result = main(args=['add', '.testfile'], cwd=repo, home=home)
        assert result == 0, f"add failed with code {result}"
        
        # Check filelist
        with open(os.path.join(repo, 'filelist'), 'r') as f:
            content = f.read()
            assert '.testfile' in content, "file not added to filelist"
        print("✓ add command works")

def test_list():
    """Test list command"""
    print("Testing 'list' command...")
    with tempfile.TemporaryDirectory() as tmpdir:
        home = os.path.join(tmpdir, 'home')
        repo = os.path.join(tmpdir, 'repo')
        os.makedirs(home)
        os.makedirs(repo)
        
        # Init and add files
        main(args=['init'], cwd=repo, home=home)
        
        test_file = os.path.join(home, '.testfile')
        with open(test_file, 'w') as f:
            f.write('test')
        
        main(args=['add', '.testfile', 'test'], cwd=repo, home=home)
        
        # Test list
        result = main(args=['list'], cwd=repo, home=home)
        assert result == 0, f"list failed with code {result}"
        print("✓ list command works")

def test_update():
    """Test update command"""
    print("Testing 'update' command...")
    with tempfile.TemporaryDirectory() as tmpdir:
        home = os.path.join(tmpdir, 'home')
        repo = os.path.join(tmpdir, 'repo')
        os.makedirs(home)
        os.makedirs(repo)
        
        # Init and add file
        main(args=['init'], cwd=repo, home=home)
        
        test_file = os.path.join(home, '.testfile')
        with open(test_file, 'w') as f:
            f.write('test')
        
        main(args=['add', '.testfile'], cwd=repo, home=home)
        
        # Test update
        result = main(args=['update', '--dry-run'], cwd=repo, home=home)
        assert result == 0, f"update failed with code {result}"
        print("✓ update command works")

def test_restore():
    """Test restore command"""
    print("Testing 'restore' command...")
    with tempfile.TemporaryDirectory() as tmpdir:
        home = os.path.join(tmpdir, 'home')
        repo = os.path.join(tmpdir, 'repo')
        os.makedirs(home)
        os.makedirs(repo)
        
        # Init and add file
        main(args=['init'], cwd=repo, home=home)
        
        test_file = os.path.join(home, '.testfile')
        with open(test_file, 'w') as f:
            f.write('test')
        
        main(args=['add', '.testfile'], cwd=repo, home=home)
        
        # Test restore
        result = main(args=['restore', '--dry-run'], cwd=repo, home=home)
        assert result == 0, f"restore failed with code {result}"
        print("✓ restore command works")

def test_clean():
    """Test clean command"""
    print("Testing 'clean' command...")
    with tempfile.TemporaryDirectory() as tmpdir:
        home = os.path.join(tmpdir, 'home')
        repo = os.path.join(tmpdir, 'repo')
        os.makedirs(home)
        os.makedirs(repo)
        
        # Init and add file
        main(args=['init'], cwd=repo, home=home)
        
        test_file = os.path.join(home, '.testfile')
        with open(test_file, 'w') as f:
            f.write('test')
        
        main(args=['add', '.testfile'], cwd=repo, home=home)
        
        # Test clean
        result = main(args=['clean', '--dry-run'], cwd=repo, home=home)
        assert result == 0, f"clean failed with code {result}"
        print("✓ clean command works")

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Running dotsync command tests...")
    print("=" * 60)
    
    tests = [
        test_init,
        test_add,
        test_list,
        test_update,
        test_restore,
        test_clean,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
    
    print("=" * 60)
    print(f"Tests passed: {passed}/{len(tests)}")
    print(f"Tests failed: {failed}/{len(tests)}")
    print("=" * 60)
    
    return failed == 0

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

