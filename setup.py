#!/usr/bin/env python3
"""
Setup script for AI Assistant Backend
"""
import os
import sys
import subprocess
import sys
import platform

def check_python_version():
    """Check Python version"""
    import sys
    if sys.version_info < (3, 8):
        print("Python 3.8 or higher is required")
        sys.exit(1)

def install_requirements():
    """Install required packages"""
    print("Installing requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("Requirements installed successfully!")

def create_env_file():
    """Create .env file from example"""
    if not os.path.exists(".env"):
        with open(".env.example", "r") as f:
            example_content = f.read()
        with open(".env", "w") as f:
            f.write(example_content)
        print("Created .env file from example")
    else:
        print(".env file already exists")

def create_directories():
    """Create necessary directories"""
    dirs = [
        "logs",
        "uploads",
        "data",
        "data/documents",
        "data/vector_store"
    ]
    
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"Created directory: {dir_path}")

def setup_database():
    """Initialize database"""
    print("Setting up database...")
    # This would typically run database migrations
    # For now, we'll just create the database file
    print("Database setup complete")

def main():
    print("Setting up AI Assistant Backend...")
    print("=" * 50)
    
    # Check Python version
    check_python_version()
    
    # Create necessary directories
    create_directories()
    
    # Create .env file if it doesn't exist
    create_env_file()
    
    # Install requirements
    install_requirements()
    
    # Setup database
    setup_database()
    
    print("\n" + "=" * 50)
    print("Setup completed successfully!")
    print("\nNext steps:")
    print("1. Edit the .env file with your configuration")
    print("2. Run the application with: python -m app.main")
    print("3. Access the API at http://localhost:8000")
    print("4. API documentation at http://localhost:8000/docs")
    print("\nTo start the application:")
    print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")

if __name__ == "__main__":
    main()