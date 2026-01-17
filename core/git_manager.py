# git_manager.py
# Manages git operations: creates branches, commits changes

import subprocess
from pathlib import Path
from typing import Optional


class GitManager:
    BRANCH_NAME = "rootcause-fixes"
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        
        if not self.project_path.is_dir():
            raise ValueError(f"Invalid project path: {self.project_path}")
        
        # Check if it's a git repository (search upward)
        self.git_root = self._find_git_root()
        if not self.git_root:
            raise RuntimeError(f"Not a git repository: {self.project_path}")
    
    def _find_git_root(self) -> Path | None:
        current = self.project_path
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent
        return None  
    def _run_git_command(self, *args) -> tuple[bool, str]:
        """
        Run a git command in the project directory
        Returns: (success: bool, output: str)
        """
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            return False, e.stderr.strip()
    
    def get_current_branch(self) -> Optional[str]:
        """Get the current branch name"""
        success, output = self._run_git_command("branch", "--show-current")
        return output if success else None
    
    def branch_exists(self, branch_name: str) -> bool:
        """Check if a branch exists (locally)"""
        success, output = self._run_git_command("branch", "--list", branch_name)
        return bool(output.strip())
    
    def create_and_switch_branch(self) -> bool:
        """
        Create the rootcause-fixes branch and switch to it
        Returns True if successful
        """
        current_branch = self.get_current_branch()
        print(f"[git] Current branch: {current_branch}")
        
        # Check if we're already on the fixes branch
        if current_branch == self.BRANCH_NAME:
            print(f"[git] Already on {self.BRANCH_NAME} branch")
            return True
        
        # Check if the branch already exists
        if self.branch_exists(self.BRANCH_NAME):
            print(f"[git] Branch {self.BRANCH_NAME} already exists, switching to it")
            success, output = self._run_git_command("checkout", self.BRANCH_NAME)
            if success:
                print(f"[git] ✓ Switched to existing branch {self.BRANCH_NAME}")
                return True
            else:
                print(f"[git] ✗ Failed to switch to branch: {output}")
                return False
        
        # Create new branch
        print(f"[git] Creating new branch: {self.BRANCH_NAME}")
        success, output = self._run_git_command("checkout", "-b", self.BRANCH_NAME)
        
        if success:
            print(f"[git] ✓ Created and switched to branch {self.BRANCH_NAME}")
            return True
        else:
            print(f"[git] ✗ Failed to create branch: {output}")
            return False
    
    def stage_file(self, file_path: str) -> bool:
        """Stage a specific file for commit"""
        success, output = self._run_git_command("add", file_path)
        if success:
            print(f"[git] ✓ Staged file: {file_path}")
            return True
        else:
            print(f"[git] ✗ Failed to stage file: {output}")
            return False
    
    def commit_changes(self, message: str) -> bool:
        """Commit staged changes"""
        success, output = self._run_git_command("commit", "-m", message)
        if success:
            print(f"[git] ✓ Committed: {message}")
            return True
        else:
            print(f"[git] ✗ Commit failed: {output}")
            return False
    
    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes"""
        success, output = self._run_git_command("status", "--porcelain")
        return bool(output.strip()) if success else False
    
    def prepare_for_fix(self) -> bool:
        """
        Prepare repository for applying fix:
        1. Check for uncommitted changes
        2. Create/switch to fixes branch if needed
        
        Returns True if ready, False otherwise
        """
        # Check if we're already on the fixes branch
        current_branch = self.get_current_branch()
        
        if current_branch != self.BRANCH_NAME:
            # First time - need to create branch
            print(f"[git] First fix application - creating branch {self.BRANCH_NAME}")
            
            # Check for uncommitted changes
            if self.has_uncommitted_changes():
                print("[git] ⚠ Warning: You have uncommitted changes")
                print("[git] These changes will be included in the new branch")
            
            return self.create_and_switch_branch()
        else:
            # Already on fixes branch - just continue
            print(f"[git] Already on {self.BRANCH_NAME} - ready for fixes")
            return True
    
    def commit_fix(self, file_path: str, reason: str) -> bool:
        """
        Stage and commit a fix
        Returns True if successful
        """
        # Make path relative to project root for cleaner commit messages
        try:
            rel_path = Path(file_path).relative_to(self.project_path)
        except ValueError:
            rel_path = Path(file_path).name
        
        if not self.stage_file(str(rel_path)):
            return False
        
        commit_message = f"fix: {reason}\n\nAuto-applied by RootCause AI"
        return self.commit_changes(commit_message)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python git_manager.py /path/to/project")
        sys.exit(1)
    
    project_path = sys.argv[1]
    
    try:
        manager = GitManager(project_path)
        
        print("\n=== Git Status ===")
        print(f"Current branch: {manager.get_current_branch()}")
        print(f"Uncommitted changes: {manager.has_uncommitted_changes()}")
        print(f"Fixes branch exists: {manager.branch_exists(GitManager.BRANCH_NAME)}")
        
        print("\n=== Testing prepare_for_fix ===")
        success = manager.prepare_for_fix()
        print(f"Result: {'✓ Success' if success else '✗ Failed'}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)