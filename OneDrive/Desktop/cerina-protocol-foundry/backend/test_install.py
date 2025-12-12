# test_install.py
print("Testing Python package installation...")
print("-" * 50)

try:
    import fastapi
    print("✓ FastAPI installed")
except ImportError as e:
    print(f"✗ FastAPI error: {e}")

try:
    import uvicorn
    print("✓ Uvicorn installed")
except ImportError as e:
    print(f"✗ Uvicorn error: {e}")

try:
    import pydantic
    print("✓ Pydantic installed")
except ImportError as e:
    print(f"✗ Pydantic error: {e}")

print("-" * 50)
print("Test complete!")