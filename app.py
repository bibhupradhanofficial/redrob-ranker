import os
import sys
import runpy

# Ensure root directory is in python search path
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Execute the sandbox app
sandbox_app_path = os.path.join(root_dir, "sandbox", "app.py")
runpy.run_path(sandbox_app_path, run_name="__main__")
