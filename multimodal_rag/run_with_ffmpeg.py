import os
import sys
import uvicorn
import static_ffmpeg

print("Initializing FFmpeg...")
static_ffmpeg.add_paths()
print("FFmpeg initialized.")

if __name__ == "__main__":
    print("Starting Uvicorn server...")
    try:
        uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=False)
    except Exception as e:
        print(f"Server crashed: {e}")
        import traceback
        traceback.print_exc()
