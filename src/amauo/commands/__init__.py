"""Command implementations for spot deployer."""

from .create import cmd_create
from .destroy import cmd_destroy
from .generate import main as cmd_generate
from .help import cmd_help
from .list import cmd_list
from .nuke import cmd_nuke
from .random_ip import cmd_random_ip
from .readme import cmd_readme
from .setup import cmd_setup
from .validate import cmd_validate
from .version import cmd_version

__all__ = [
    "cmd_create",
    "cmd_destroy",
    "cmd_generate",
    "cmd_list",
    "cmd_nuke",
    "cmd_random_ip",
    "cmd_setup",
    "cmd_help",
    "cmd_readme",
    "cmd_validate",
    "cmd_version",
]
