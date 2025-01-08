import os
import subprocess
import sys

def main():
    # Get the directory where the launcher executable is located
    current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    
    # Path to the main executable and its directory
    exe_dir = os.path.join(current_dir, "TradevLink Connector")
    exe_path = os.path.join(exe_dir, "TradevLink Connector.exe")
    
    try:
        # Start the main executable from its directory so it can find its assets
        subprocess.Popen([exe_path], cwd=exe_dir)
    except Exception as e:
        print(f"Error launching TradevLink Connector: {e}")

if __name__ == "__main__":
    main()
