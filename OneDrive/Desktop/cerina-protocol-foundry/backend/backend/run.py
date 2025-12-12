# backend/run.py
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print(f"Python path: {sys.path[0]}")

# Now import and run the main module
if __name__ == "__main__":
    try:
        import main
        print("✅ Main module imported successfully")
        
        # Check if the API is available
        if hasattr(main, 'api'):
            import uvicorn
            print("\n" + "="*60)
            print("🚀 Starting Cerina Protocol Foundry Backend")
            print("="*60)
            print(f"🌐 Server will be available at: http://localhost:8000")
            print(f"📚 API Documentation: http://localhost:8000/docs")
            print(f"⚡ Using reload mode for development")
            print("="*60)
            
            uvicorn.run("main:api", host="0.0.0.0", port=8000, reload=True)
        else:
            print("❌ No 'api' object found in main module")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")