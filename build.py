import PyInstaller.__main__
import os
import sys
import shutil
import importlib.util
import win32com.client
from utils.version import TRADEVLINK_VERSION

def clean_dist():
    """Clean up previous build artifacts"""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    # Also remove spec file if it exists
    spec_file = 'App.spec'
    if os.path.exists(spec_file):
        os.remove(spec_file)

def create_shortcut(target_path, shortcut_path, icon_path=None):
    """Create a Windows shortcut (.lnk) file"""
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = target_path
    shortcut.WorkingDirectory = os.path.dirname(target_path)
    if icon_path and os.path.exists(icon_path):
        shortcut.IconLocation = icon_path
    shortcut.save()

def update_version_file():
    """Update version.txt with current version from utils/version.py"""
    # Convert version string (e.g., "1.0.0-1") to tuple (1, 0, 0, 1)
    version_parts = TRADEVLINK_VERSION.replace('-', '.').split('.')
    version_tuple = tuple(int(part) for part in version_parts)
    
    version_content = f'''VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'TradevLink'),
        StringStruct(u'FileDescription', u'TradevLink Connector'),
        StringStruct(u'FileVersion', u'{TRADEVLINK_VERSION}'),
        StringStruct(u'InternalName', u'TradevLink Connector'),
        StringStruct(u'LegalCopyright', u'Copyright (c) 2024 TradevLink'),
        StringStruct(u'OriginalFilename', u'TradevLink Connector.exe'),
        StringStruct(u'ProductName', u'TradevLink Connector'),
        StringStruct(u'ProductVersion', u'{TRADEVLINK_VERSION}')])
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)'''
    
    with open('version.txt', 'w') as f:
        f.write(version_content.replace('{TRADEVLINK_VERSION}', TRADEVLINK_VERSION))

def build():
    # Clean previous builds
    clean_dist()
    
    # Update version.txt with current version
    update_version_file()
    
    # Get CustomTkinter path dynamically
    customtkinter_spec = importlib.util.find_spec('customtkinter')
    if customtkinter_spec is None:
        raise ImportError("customtkinter package not found. Please ensure it is installed.")
    customtkinter_path = os.path.dirname(customtkinter_spec.origin)
    print(f"Found customtkinter at: {customtkinter_path}")
    
    # Ensure the assets directory exists
    if not os.path.exists('assets'):
        print("Warning: assets directory not found")
        os.makedirs('assets', exist_ok=True)
    
    # Check if icon exists
    icon_path = os.path.join('assets', 'logo.ico')
    if not os.path.exists(icon_path):
        print(f"Warning: Icon file not found at {icon_path}")
    
    # Build command
    cmd = [
        'main.py',
        '--name=TradevLink Connector',
        '--onedir',
        '--windowed',
        '--version-file=version.txt',
        '--specpath=.',
        '--workpath=build',
        '--distpath=dist',
        '--noconfirm',
        '--add-data=gui;gui',
        '--add-data=utils;utils',
        '--add-data=assets;assets',
        '--add-data=config.example.json;.',
        f'--add-data={customtkinter_path};customtkinter',
        '--collect-data=customtkinter',
        '--collect-data=darkdetect',
        '--python-option=O',
        f'--icon={icon_path}' if os.path.exists(icon_path) else None,
    ]
    
    try:
        print("Starting PyInstaller build process...")
        PyInstaller.__main__.run(cmd)
        print("Build completed successfully!")
        
        # Create shortcut in dist folder
        exe_path = os.path.join('dist', 'TradevLink Connector', 'TradevLink Connector.exe')
        shortcut_path = os.path.join('dist', 'TradevLink Connector.lnk')
        icon_path = os.path.abspath(os.path.join('assets', 'logo.ico'))
        if os.path.exists(exe_path):
            create_shortcut(os.path.abspath(exe_path), os.path.abspath(shortcut_path), icon_path)
            print(f"Created shortcut at: {shortcut_path}")
        
    except Exception as e:
        print(f"Build failed: {e}")
        raise

if __name__ == "__main__":
    build()
