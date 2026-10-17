"""Launcher for build_size.py under a project-unique process name (other builders pkill by 'build_size.py', ENGINE_NOTES 3)."""
import runpy, sys
sys.argv[0] = "build_size.py"
runpy.run_path("build_size.py", run_name="__main__")
