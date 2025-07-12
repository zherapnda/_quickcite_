import os
import subprocess
from pathlib import Path
import whisper
import json
from typing import Dict, List, Tuple
import tempfile

class AudioTranscriber:
    """Handles audio extraction and transcription from various file formats"""
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize the transcriber with Whisper model
        
        Args:
            model_size: Size of Whisper model - tiny, base, small, medium, large
        """
        print(f"Loading Whisper model: {model_size}")
        self.model = whisper.load_model(model_size)
        self.supported_formats = ['.mp4', '.mp3', '.wav', '.m4a', '.avi', '.mov']
        
    def extract_audio_from_video(self, video_path: str, output_path: str = None) -> str:
        """
        Extract audio from video file using ffmpeg
        
        Args:
            video_path: Path to video file
            output_path: Optional output path for audio file
            
        Returns:
            Path to extracted audio file
        """
        if output_path is None:
            # Create temporary file for audio
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, "extracted_audio.wav")
        
        try:
            # Use ffmpeg to extract audio
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-acodec', 'pcm_s16le',
                '-ar', '16000',  # 16kHz sample rate for Whisper
                '-ac', '1',      # Mono audio
                '-y',            # Overwrite output file
                output_path
            ]
            
            # Run ffmpeg
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"FFmpeg error: {result.stderr}")
                raise Exception(f"Failed to extract audio: {result.stderr}")
            
            return output_path
            
        except FileNotFoundError:
            raise Exception("FFmpeg not found. Please install FFmpeg and add it to PATH")
        except Exception as e:
            raise Exception(f"Audio extraction failed: {str(e)}")
    
    def transcribe_audio(self, audio_path: str) -> Dict:
        """
        Transcribe audio file using Whisper
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary containing transcription and metadata
        """
        print(f"Transcribing audio file: {audio_path}")
        
        # Transcribe with Whisper
        result = self.model.transcribe(
            audio_path,
            fp16=False,  # Use FP32 for better compatibility
            language="en",  # Specify English for better accuracy
            task="transcribe"
        )
        
        # Extract segments with timestamps
        segments = []
        for segment in result.get("segments", []):
            segments.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"].strip(),
                "confidence": segment.get("avg_logprob", 0)
            })
        
        return {
            "text": result["text"].strip(),
            "segments": segments,
            "language": result.get("language", "en"),
            "duration": segments[-1]["end"] if segments else 0
        }
    
    def process_media_file(self, media_path: str) -> Dict:
        """
        Process any supported media file (video or audio)
        
        Args:
            media_path: Path to media file
            
        Returns:
            Transcription results
        """
        file_ext = Path(media_path).suffix.lower()
        
        if file_ext not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Check if it's a video file that needs audio extraction
        video_formats = ['.mp4', '.avi', '.mov']
        
        if file_ext in video_formats:
            # Extract audio first
            print(f"Extracting audio from video: {media_path}")
            audio_path = self.extract_audio_from_video(media_path)
            
            try:
                # Transcribe the extracted audio
                result = self.transcribe_audio(audio_path)
            finally:
                # Clean up temporary audio file
                if os.path.exists(audio_path) and "temp" in audio_path:
                    os.remove(audio_path)
        else:
            # Direct audio file
            result = self.transcribe_audio(media_path)
        
        return result
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract common entities from transcribed text
        This is a simple implementation - can be enhanced with spaCy or other NLP
        
        Args:
            text: Transcribed text
            
        Returns:
            Dictionary of entity types and their values
        """
        import re
        
        entities = {
            "dates": [],
            "emails": [],
            "phone_numbers": [],
            "names": [],
            "addresses": [],
            "numbers": []
        }
        
        # Extract dates (simple patterns)
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b'
        ]
        
        for pattern in date_patterns:
            entities["dates"].extend(re.findall(pattern, text, re.IGNORECASE))
        
        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        entities["emails"].extend(re.findall(email_pattern, text))
        
        # Extract phone numbers
        phone_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',
            r'\b\d{10}\b'
        ]
        
        for pattern in phone_patterns:
            entities["phone_numbers"].extend(re.findall(pattern, text))
        
        # Extract numbers (for things like SSN, employee ID, etc.)
        number_pattern = r'\b\d{2,}\b'
        entities["numbers"].extend(re.findall(number_pattern, text))
        
        # Remove duplicates
        for key in entities:
            entities[key] = list(set(entities[key]))
        
        return entities
    
    def save_transcription(self, transcription: Dict, output_path: str):
        """Save transcription results to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(transcription, f, indent=2, ensure_ascii=False)
        print(f"Transcription saved to: {output_path}")


# Example usage
if __name__ == "__main__":
    # Initialize transcriber
    transcriber = AudioTranscriber(model_size="base")
    
    # Example: Process a media file
    # media_path = "path/to/your/video.mp4"
    # result = transcriber.process_media_file(media_path)
    # 
    # print("Transcription:")
    # print(result["text"])
    # 
    # # Extract entities
    # entities = transcriber.extract_entities(result["text"])
    # print("\nExtracted entities:")
    # for entity_type, values in entities.items():
    #     if values:
    #         print(f"{entity_type}: {values}")