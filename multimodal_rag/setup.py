"""Setup script for Multimodal RAG System."""
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return False


def main():
    """Main setup routine."""
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║                                                        ║
    ║       MULTIMODAL RAG SYSTEM - SETUP WIZARD            ║
    ║                                                        ║
    ║  Evidence-Based Multimodal Retrieval & Generation     ║
    ║                                                        ║
    ║          Team: ManageSphere | Table No. 18            ║
    ║                                                        ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("❌ Error: Python 3.9 or higher required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version.split()[0]} detected")
    
    # Install dependencies
    print("\n📦 Installing dependencies...")
    if not run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Installing Python packages"
    ):
        print("\n⚠️  Some packages failed to install. Please check errors above.")
        choice = input("\nContinue anyway? (y/n): ")
        if choice.lower() != 'y':
            sys.exit(1)
    
    # Create directories
    print("\n📁 Creating data directories...")
    dirs = [
        "data/uploads",
        "data/processed",
        "data/chroma_db",
        "logs"
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {dir_path}")
    
    # Check for .env file
    print("\n⚙️  Checking configuration...")
    env_file = Path(".env")
    if not env_file.exists():
        print("  Creating .env from template...")
        import shutil
        shutil.copy(".env.example", ".env")
        print("  ✓ .env created")
    else:
        print("  ✓ .env already exists")
    
    # Check Ollama (optional)
    print("\n🤖 Checking for Ollama (optional)...")
    try:
        result = subprocess.run(
            "ollama --version",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"  ✅ Ollama detected: {result.stdout.strip()}")
            print("\n  Checking for llama3.2:3b model...")
            result = subprocess.run(
                "ollama list",
                shell=True,
                capture_output=True,
                text=True
            )
            if "llama3.2:3b" in result.stdout:
                print("  ✅ llama3.2:3b model already installed")
            else:
                print("  ⚠️  llama3.2:3b not found")
                print("\n  To install, run: ollama pull llama3.2:3b")
        else:
            print("  ⚠️  Ollama not found")
    except FileNotFoundError:
        print("  ⚠️  Ollama not installed")
        print("\n  Download from: https://ollama.ai")
        print("  Then run: ollama pull llama3.2:3b")
    
    print("\n" + "="*60)
    print("  ✅ SETUP COMPLETE!")
    print("="*60)
    
    print("""
    🚀 Next Steps:
    
    1. (Optional) Install Ollama and pull llama3.2:3b model
       Or configure OPENROUTER_API_KEY in .env
    
    2. Start the server:
       cd backend
       python app.py
    
    3. Open in browser:
       http://localhost:8000
    
    4. Upload documents and start querying!
    
    📚 Documentation: README.md
    🐛 Logs: logs/ directory
    """)


if __name__ == "__main__":
    main()
