"""Generate a test audio file using text-to-speech."""
import os

# Create a simple text file that will be converted to speech
text_content = """
Hello, this is a test audio file for the Multimodal RAG System.
This audio discusses the CHAKRAVYUH 1.0 Hackathon.
CHAKRAVYUH is a national level hackathon happening on 30th and 31st January 2026.
It's a 36-hour nonstop coding competition at GITA Autonomous College in Bhubaneshwar.
The prize pool is one lakh rupees.
This is a great opportunity for students to showcase their skills.
"""

# Save the transcription text (simulating what Whisper would extract)
with open('test_audio_transcription.txt', 'w') as f:
    f.write(text_content)

print("✅ Test audio transcription created: test_audio_transcription.txt")
print("Note: For a real audio file, you would need audio generation libraries.")
print("For this demo, we'll use the transcription text directly.")
