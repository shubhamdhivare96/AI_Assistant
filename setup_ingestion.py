"""
Setup script to check and install required packages for ingestion
"""
import subprocess
import sys

def check_package(package_name):
    """Check if a package is installed"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def install_package(package_name):
    """Install a package using pip"""
    print(f"Installing {package_name}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
    print(f"✓ {package_name} installed")

def main():
    """Check and install required packages"""
    print("=" * 80)
    print("Ingestion Setup - Checking Dependencies")
    print("=" * 80)
    
    required_packages = {
        'qdrant_client': 'qdrant-client',
        'sentence_transformers': 'sentence-transformers',
        'dotenv': 'python-dotenv'
    }
    
    missing_packages = []
    
    # Check each package
    for import_name, package_name in required_packages.items():
        print(f"\nChecking {package_name}...", end=" ")
        if check_package(import_name):
            print("✓ Installed")
        else:
            print("✗ Missing")
            missing_packages.append(package_name)
    
    # Install missing packages
    if missing_packages:
        print("\n" + "-" * 80)
        print(f"Installing {len(missing_packages)} missing packages...")
        print("-" * 80)
        
        for package in missing_packages:
            try:
                install_package(package)
            except Exception as e:
                print(f"✗ Failed to install {package}: {e}")
                return False
        
        print("\n" + "=" * 80)
        print("✓ All dependencies installed!")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("✓ All dependencies already installed!")
        print("=" * 80)
    
    print("\nYou can now run:")
    print("  python ingest_docs_simple.py")
    print("\nOr for advanced features:")
    print("  python ingest_python_docs.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
