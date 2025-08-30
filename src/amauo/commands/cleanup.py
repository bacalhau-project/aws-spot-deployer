"""Cleanup command for removing temporary files and preventing conflicts."""

import subprocess
from pathlib import Path

from ..utils.display import console, rich_print, rich_success


def cmd_cleanup():
    """Run aggressive cleanup to remove temporary files and prevent conflicts."""
    rich_print("🧹 [bold]Running aggressive cleanup...[/bold]")
    
    cleanup_script = Path(__file__).parent.parent.parent.parent / "scripts" / "cleanup.sh"
    
    if not cleanup_script.exists():
        console.print("❌ Cleanup script not found. Please ensure scripts/cleanup.sh exists.")
        return
    
    try:
        result = subprocess.run([str(cleanup_script)], check=True, capture_output=True, text=True)
        console.print(result.stdout)
        rich_success("Cleanup completed successfully!")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Cleanup failed: {e}")
        if e.stdout:
            console.print("STDOUT:", e.stdout)
        if e.stderr:
            console.print("STDERR:", e.stderr)
    except Exception as e:
        console.print(f"❌ Unexpected error during cleanup: {e}")