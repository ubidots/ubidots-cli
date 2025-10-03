#!/usr/bin/env python3
"""
Build script for the Ubidots Pages Docker image.
This script builds the custom Docker image with pre-installed dependencies.
"""

import subprocess
import sys
from pathlib import Path


def build_pages_image():
    """Build the Ubidots Pages Docker image."""

    # Get the directory containing this script
    script_dir = Path(__file__).parent
    dockerfile_path = script_dir / "Dockerfile"
    page_server_path = script_dir.parent / "templates" / "page_server.py"

    # Verify required files exist
    if not dockerfile_path.exists():
        print(f"Error: Dockerfile not found at {dockerfile_path}")
        return False

    if not page_server_path.exists():
        print(f"Error: page_server.py not found at {page_server_path}")
        return False

    # Copy page_server.py to build context
    import shutil

    build_context = script_dir
    shutil.copy2(page_server_path, build_context / "page_server.py")

    try:
        # Build the Docker image
        image_name = "ubidots/pages-server:latest"
        print(f"Building Docker image: {image_name}")
        print(f"Build context: {build_context}")

        result = subprocess.run(
            [
                "docker",
                "build",
                "-t",
                image_name,
                "-f",
                str(dockerfile_path),
                str(build_context),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        print("✓ Docker image built successfully!")
        print(f"Image: {image_name}")

        # Clean up copied file
        (build_context / "page_server.py").unlink()

        return True

    except subprocess.CalledProcessError as e:
        print(f"Error building Docker image:")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")

        # Clean up copied file
        copied_file = build_context / "page_server.py"
        if copied_file.exists():
            copied_file.unlink()

        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = build_pages_image()
    sys.exit(0 if success else 1)
