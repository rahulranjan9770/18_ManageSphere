"""Quick test script to verify installation and start server."""
import sys
import subprocess
from pathlib import Path

def check_import(module_name, package_name=None):
    """Check if a module can be imported."""
    package = package_name or module_name
    try:
        __import__(module_name)
        print(f"  ✓ {package}")
        return True
    except ImportError:
        print(f"  ✗ {package} - NOT INSTALLED")
        return False

def main():
    print("="*60)
    print("  MULTIMODAL RAG - SYSTEM CHECK")
    print("="*60)
    
    print("\n📦 Checking Python packages...\n")
    
    checks = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("pydantic", "pydantic"),
        ("chromadb", "chromadb"),
        ("sentence_transformers", "sentence-transformers"),
        ("torch", "torch"),
        ("PIL", "pillow"),
        ("pypdf", "pypdf"),
        ("docx", "python-docx"),
        ("numpy", "numpy"),
        ("sklearn", "scikit-learn"),
    ]
    
    all_ok = True
    for module, package in checks:
        if not check_import(module, package):
            all_ok = False
    
    print("\n🤖 Checking Ollama...\n")
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True
        )
        if "llama3.2" in result.stdout:
            print("  ✓ Ollama installed with llama3.2 model")
        else:
            print("  ⚠ Ollama installed but llama3.2:3b not found")
            print("  Run: ollama pull llama3.2:3b")
    except FileNotFoundError:
        print("  ✗ Ollama not found")
    
    print("\n" + "="*60)
    
    if all_ok:
        print("  ✅ ALL DEPENDENCIES INSTALLED!")
        print("="*60)
        print("\n🚀 Starting server...\n")
        
        # Start the server
        import os
        os.chdir("backend")
        subprocess.run([sys.executable, "app.py"])
    else:
        print("  ⚠ MISSING DEPENDENCIES")
        print("="*60)
        print("\n📝 To install missing packages:")
        print("  python -m pip install -r requirements.txt")
        print("\n  OR run the setup wizard:")
        print("  python setup.py")

if __name__ == "__main__":
    main()
