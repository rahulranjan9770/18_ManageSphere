print("Initializing FFmpeg...")
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
    print("FFmpeg initialized successfully!")
except Exception as e:
    print(f"Failed to initialize FFmpeg: {e}")
