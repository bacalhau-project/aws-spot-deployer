#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""Apply the two-stage deployment patch to deploy_spot.py"""

import os
import shutil

print("Applying two-stage deployment patch...")

# First, backup the current file
if not os.path.exists("deploy_spot.py.backup2"):
    shutil.copy("deploy_spot.py", "deploy_spot.py.backup2")
    print("✓ Created backup: deploy_spot.py.backup2")

# Read the current file
with open("deploy_spot.py", "r") as f:
    content = f.read()

# Find where to insert the new functions
import_section_end = content.find("# Rich console for output")
if import_section_end == -1:
    import_section_end = content.find("console = Console()")

# Add tarfile import if not present
if "import tarfile" not in content:
    insert_pos = content.rfind("import", 0, import_section_end)
    insert_pos = content.find("\n", insert_pos) + 1
    content = content[:insert_pos] + "import tarfile\n" + content[insert_pos:]
    print("✓ Added tarfile import")

# Find and replace the generate_full_cloud_init function
start_marker = "def generate_full_cloud_init(config: SimpleConfig) -> str:"
end_marker = '\n    return "\\n".join(cloud_init_parts)\n'

start_pos = content.find(start_marker)
if start_pos == -1:
    print("❌ Could not find generate_full_cloud_init function")
    exit(1)

# Find the end of the function
end_pos = content.find(end_marker, start_pos)
if end_pos == -1:
    # Try alternative end marker
    end_marker = '\n    return cloud_init\n'
    end_pos = content.find(end_marker, start_pos)
    if end_pos == -1:
        print("❌ Could not find end of generate_full_cloud_init function")
        exit(1)

end_pos += len(end_marker)

# Read the new function
with open("minimal_cloud_init_function.py", "r") as f:
    new_function = f.read()

# Replace the function
content = content[:start_pos] + new_function + content[end_pos:]
print("✓ Replaced generate_full_cloud_init with minimal version")

# Add the bundle functions after generate_full_cloud_init
with open("bundle_functions.py", "r") as f:
    bundle_functions = f.read()

# Find where to insert (after the new generate_full_cloud_init)
insert_pos = content.find("def wait_for_instance_ready", start_pos)
if insert_pos != -1:
    content = content[:insert_pos] + "\n" + bundle_functions + "\n\n" + content[insert_pos:]
    print("✓ Added bundle creation and upload functions")

# Now modify wait_for_instance_ready to upload the bundle
# Find the line where it says "Instance accessible"
accessible_marker = '"SSH: Connection", 100, "SSH connection established"'
accessible_pos = content.find(accessible_marker)

if accessible_pos != -1:
    # Find the end of that code block
    next_line_pos = content.find("\n", accessible_pos)
    indent_start = content.rfind("\n", 0, accessible_pos) + 1
    indent = content[indent_start:accessible_pos].replace(content[indent_start:accessible_pos].lstrip(), "")
    
    # Insert bundle upload code
    bundle_upload_code = f'''
{indent}            # Upload deployment bundle after SSH is ready
{indent}            if elapsed > 20:  # Give cloud-init time to set up
{indent}                # Create bundle once
{indent}                if not hasattr(wait_for_instance_ready, '_bundle_file'):
{indent}                    update_progress("Bundle", 60, "Creating deployment bundle...")
{indent}                    wait_for_instance_ready._bundle_file = create_deployment_bundle(config)
{indent}                
{indent}                # Upload bundle
{indent}                update_progress("Upload", 70, "Uploading deployment files...")
{indent}                if upload_deployment_bundle(hostname, username, private_key_path, 
{indent}                                           wait_for_instance_ready._bundle_file, logger):
{indent}                    update_progress("Upload", 85, "Deployment files uploaded")
{indent}                    # Give the instance time to extract and start services
{indent}                    time.sleep(5)
{indent}                    return True
{indent}                else:
{indent}                    update_progress("Upload", 70, "Upload failed, retrying...")'''
    
    # Insert at a better location - after SSH is established
    insert_marker = "time.sleep(2)  # Brief pause before cloud-init check"
    insert_pos = content.find(insert_marker, accessible_pos)
    if insert_pos != -1:
        insert_pos = content.find("\n", insert_pos) + 1
        content = content[:insert_pos] + bundle_upload_code + "\n" + content[insert_pos:]
        print("✓ Added bundle upload logic to wait_for_instance_ready")

# Write the modified file
with open("deploy_spot.py", "w") as f:
    f.write(content)

print("\n✅ Patch applied successfully!")
print("\nThe deployment now uses a two-stage process:")
print("1. Minimal cloud-init (3.6KB) sets up and waits for files")
print("2. deploy_spot.py uploads bundle (22.7KB) after SSH is ready")
print("\nTest with: uv run -s deploy_spot.py create")