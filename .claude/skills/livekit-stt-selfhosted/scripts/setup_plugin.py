#!/usr/bin/env python3
"""
Setup script for creating a new LiveKit STT plugin from template.

Usage:
    python setup_plugin.py <plugin-name> [--output-dir OUTPUT_DIR]

Example:
    python setup_plugin.py whisper-stt --output-dir ./my-plugins
"""

import argparse
import shutil
from pathlib import Path


def setup_plugin(plugin_name: str, output_dir: Path, template_dir: Path):
    """
    Create a new LiveKit STT plugin from the template.

    Args:
        plugin_name: Name for the plugin (e.g., 'whisper-stt')
        output_dir: Directory where the plugin will be created
        template_dir: Path to the plugin template
    """
    # Validate plugin name
    if not plugin_name.replace("-", "").replace("_", "").isalnum():
        raise ValueError(f"Invalid plugin name: {plugin_name}")

    # Create plugin directory name
    plugin_dir_name = f"livekit-plugins-{plugin_name}"
    plugin_path = output_dir / plugin_dir_name

    # Check if directory already exists
    if plugin_path.exists():
        raise FileExistsError(f"Plugin directory already exists: {plugin_path}")

    print(f"Creating plugin: {plugin_dir_name}")
    print(f"Location: {plugin_path}")

    # Copy template
    shutil.copytree(template_dir, plugin_path)

    # Replace placeholders in files
    package_name = plugin_name.replace("-", "_")

    # Rename the package directory
    old_package_dir = plugin_path / "livekit" / "plugins" / "custom_stt"
    new_package_dir = plugin_path / "livekit" / "plugins" / package_name

    if old_package_dir.exists():
        old_package_dir.rename(new_package_dir)

    # Update files with actual plugin name
    files_to_update = [
        plugin_path / "pyproject.toml",
        plugin_path / "README.md",
        new_package_dir / "__init__.py",
    ]

    for file_path in files_to_update:
        if file_path.exists():
            content = file_path.read_text()
            content = content.replace("custom-stt", plugin_name)
            content = content.replace("custom_stt", package_name)
            content = content.replace("yourname", package_name)
            file_path.write_text(content)

    print(f"\n✅ Plugin created successfully!")
    print(f"\nNext steps:")
    print(f"1. cd {plugin_path}")
    print(f"2. Update pyproject.toml with your details")
    print(f"3. Edit livekit/plugins/{package_name}/stt.py to connect to your API")
    print(f"4. pip install -e .")
    print(f"5. Test your plugin")


def main():
    parser = argparse.ArgumentParser(
        description="Create a new LiveKit STT plugin from template"
    )
    parser.add_argument("plugin_name", help="Name for the plugin (e.g., 'whisper-stt')")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory where the plugin will be created (default: current directory)",
    )

    args = parser.parse_args()

    # Get the template directory (relative to this script)
    script_dir = Path(__file__).parent
    template_dir = script_dir.parent / "assets" / "plugin-template"

    if not template_dir.exists():
        print(f"❌ Error: Template directory not found: {template_dir}")
        return 1

    try:
        setup_plugin(args.plugin_name, args.output_dir, template_dir)
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
