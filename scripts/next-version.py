#!/usr/bin/env uv run
# /// script
# requires-python = ">=3.9"
# dependencies = ["semver>=3.0.0"]
# ///
"""
Get the next semantic version and output a ready-to-run command.
"""

import subprocess

import semver


def run_git_command(cmd):
    """Run a git command and return output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def get_latest_version():
    """Get the latest semantic version tag."""
    # Fetch tags
    run_git_command(["git", "fetch", "--tags", "-f"])

    # Get all tags and find semantic versions
    tags = run_git_command(["git", "tag", "-l", "v*"]).split("\n")

    versions = []
    for tag in tags:
        if tag.startswith("v"):
            try:
                version = semver.Version.parse(tag[1:])
                versions.append((tag, version))
            except ValueError:
                continue

    if not versions:
        return "v0.0.0", semver.Version(0, 0, 0)

    versions.sort(key=lambda x: x[1])
    return versions[-1]


def main():
    latest_tag, latest_version = get_latest_version()
    next_version = latest_version.bump_patch()
    next_tag = f"v{next_version}"

    print(f"Current: {latest_tag}")
    print(f"Next:    {next_tag}")
    print()
    print("Copy and run this command:")
    print(
        f"git commit -am 'Release {next_tag}' && git tag {next_tag} && git push && git push origin {next_tag}"
    )


if __name__ == "__main__":
    main()
