"""
Install Missing Packages
Checks for missing packages and installs them
"""
import subprocess
import sys

# List of required packages that might be missing
REQUIRED_PACKAGES = [
    "rank-bm25",
    "faiss-cpu",
    "psutil",
    # "prometheus-client",  # FUTURE SCOPE - not needed for assignment
]

def check_package(package_name):
    """Check if a package is installed"""
    try:
        __import__(package_name.replace("-", "_"))
        return True
    except ImportError:
        return False

def install_package(package_name):
    """Install a package using pip"""
    print(f"Installing {package_name}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"✓ {package_name} installed successfully")
        return True
    except subprocess.CalledProcessError:
        print(f"✗ Failed to install {package_name}")
        return False

def main():
    print("Checking for missing packages...\n")
    
    missing_packages = []
    
    for package in REQUIRED_PACKAGES:
        # Convert package name to import name
        import_name = package.replace("-", "_")
        if import_name == "faiss_cpu":
            import_name = "faiss"
        elif import_name == "prometheus_client":
            import_name = "prometheus_client"
        
        if not check_package(import_name):
            missing_packages.append(package)
            print(f"✗ {package} is missing")
        else:
            print(f"✓ {package} is installed")
    
    if not missing_packages:
        print("\n✓ All required packages are installed!")
        return
    
    print(f"\nFound {len(missing_packages)} missing package(s)")
    print("Installing missing packages...\n")
    
    for package in missing_packages:
        install_package(package)
    
    print("\n✓ Installation complete!")
    print("\nYou can now start the backend:")
    print("  python app/main.py")

if __name__ == "__main__":
    main()
