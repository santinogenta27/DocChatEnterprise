"""
Asset Processor Service
Analyzes images, videos, and text using AI vision and audio models
"""
import os
import uuid
from typing import Dict, Any, List, Optional
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import whisper
import librosa
from datetime import datetime

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI no disponible. Instala con: pip install openai")

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from ..models.schemas import AssetType, AssetAnalysis


class AssetProcessor:
    """Processes and analyzes user-uploaded assets (images, videos, text)"""
    
    def __init__(self, openai_api_key: Optional[str] = None, storage_path: str = "./assets"):
        self.openai_client = None
        if OPENAI_AVAILABLE and openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize Whisper for audio transcription
        self.whisper_model = None
        if TORCH_AVAILABLE:
            try:
                self.whisper_model = whisper.load_model("base")
            except Exception as e:
                print(f"⚠️ No se pudo cargar modelo Whisper: {e}")
    
    def process_asset(
        self,
        asset_type: AssetType,
        file_path: Optional[str] = None,
        file_url: Optional[str] = None,
        text_content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AssetAnalysis:
        """
        Main method to process any type of asset
        
        Args:
            asset_type: Type of asset (image, video, text)
            file_path: Local file path
            file_url: URL to file
            text_content: Text content (for text assets)
            metadata: Additional metadata
            
        Returns:
            AssetAnalysis with all extracted information
        """
        asset_id = str(uuid.uuid4())
        
        if asset_type == AssetType.IMAGE:
            return self._analyze_image(asset_id, file_path, file_url, metadata)
        elif asset_type == AssetType.VIDEO:
            return self._analyze_video(asset_id, file_path, file_url, metadata)
        elif asset_type == AssetType.TEXT:
            return self._analyze_text(asset_id, text_content, metadata)
        else:
            raise ValueError(f"Unsupported asset type: {asset_type}")
    
    def _analyze_image(
        self,
        asset_id: str,
        file_path: Optional[str],
        file_url: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ) -> AssetAnalysis:
        """Analyze image using vision models"""
        # Load image
        if file_path:
            img_path = file_path
        elif file_url:
            # Download from URL (simplified - in production use proper download)
            img_path = self._download_file(file_url, asset_id, "image")
        else:
            raise ValueError("Either file_path or file_url must be provided")
        
        # Get image info
        img = Image.open(img_path)
        width, height = img.size
        file_size = os.path.getsize(img_path)
        
        # Analyze with OpenAI Vision if available
        labels = []
        objects_detected = []
        dominant_colors = []
        style_tags = []
        emotion_tags = []
        
        if self.openai_client:
            try:
                # Use GPT-4 Vision for analysis
                with open(img_path, "rb") as image_file:
                    response = self.openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": """Analyze this image and provide:
1. Main labels/tags (comma-separated)
2. Objects detected (JSON format: [{"name": "...", "confidence": 0.0-1.0}])
3. Dominant colors (hex codes)
4. Style tags (e.g., minimalist, professional, vibrant)
5. Emotion tags (e.g., happy, serious, energetic)
                                        
Return JSON format:
{
    "labels": ["tag1", "tag2"],
    "objects": [{"name": "object", "confidence": 0.9}],
    "colors": ["#FFFFFF", "#000000"],
    "style": ["minimalist", "professional"],
    "emotion": ["serious", "professional"]
}"""
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"file://{img_path}"}
                                    }
                                ]
                            }
                        ],
                        max_tokens=500
                    )
                    
                    # Parse response (simplified - in production use proper JSON parsing)
                    content = response.choices[0].message.content
                    # Extract JSON from response (basic parsing)
                    import json
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        analysis = json.loads(json_match.group())
                        labels = analysis.get("labels", [])
                        objects_detected = analysis.get("objects", [])
                        dominant_colors = analysis.get("colors", [])
                        style_tags = analysis.get("style", [])
                        emotion_tags = analysis.get("emotion", [])
            except Exception as e:
                print(f"⚠️ Error en análisis con OpenAI Vision: {e}")
                # Fallback to basic analysis
                labels = self._basic_image_analysis(img_path)
        
        # Extract key frames (for images, just the image itself)
        key_frames = [img_path]
        
        return AssetAnalysis(
            asset_id=asset_id,
            asset_type=AssetType.IMAGE,
            labels=labels,
            objects_detected=objects_detected,
            dominant_colors=dominant_colors,
            style_tags=style_tags,
            emotion_tags=emotion_tags,
            resolution={"width": width, "height": height},
            file_size=file_size,
            format=Path(img_path).suffix[1:].upper()
        )
    
    def _analyze_video(
        self,
        asset_id: str,
        file_path: Optional[str],
        file_url: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ) -> AssetAnalysis:
        """Analyze video using vision and audio models"""
        # Load video
        if file_path:
            video_path = file_path
        elif file_url:
            video_path = self._download_file(file_url, asset_id, "video")
        else:
            raise ValueError("Either file_path or file_url must be provided")
        
        # Get video info using OpenCV
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0
        file_size = os.path.getsize(video_path)
        
        # Extract key frames
        key_frames = self._extract_key_frames(video_path, asset_id)
        
        # Transcribe audio
        transcript = None
        if self.whisper_model:
            try:
                result = self.whisper_model.transcribe(video_path)
                transcript = result["text"]
            except Exception as e:
                print(f"⚠️ Error en transcripción de audio: {e}")
        
        # Analyze key frames (use first frame for now)
        frame_analysis = None
        if key_frames and self.openai_client:
            try:
                frame_analysis = self._analyze_image(asset_id, key_frames[0], None, metadata)
            except:
                pass
        
        labels = frame_analysis.labels if frame_analysis else []
        objects_detected = frame_analysis.objects_detected if frame_analysis else []
        style_tags = frame_analysis.style_tags if frame_analysis else []
        emotion_tags = frame_analysis.emotion_tags if frame_analysis else []
        
        cap.release()
        
        return AssetAnalysis(
            asset_id=asset_id,
            asset_type=AssetType.VIDEO,
            labels=labels,
            objects_detected=objects_detected,
            style_tags=style_tags,
            emotion_tags=emotion_tags,
            duration=duration,
            key_frames=key_frames,
            transcript=transcript,
            resolution={"width": width, "height": height},
            file_size=file_size,
            format=Path(video_path).suffix[1:].upper()
        )
    
    def _analyze_text(
        self,
        asset_id: str,
        text_content: str,
        metadata: Optional[Dict[str, Any]]
    ) -> AssetAnalysis:
        """Analyze text content"""
        if not text_content:
            raise ValueError("text_content is required for text assets")
        
        # Basic text analysis
        keywords = self._extract_keywords(text_content)
        topics = self._extract_topics(text_content)
        sentiment = self._analyze_sentiment(text_content)
        
        # Use OpenAI for advanced analysis if available
        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert at analyzing marketing text. Extract labels, keywords, topics, and sentiment."
                        },
                        {
                            "role": "user",
                            "content": f"Analyze this marketing text:\n\n{text_content}\n\nProvide labels, keywords, topics, and sentiment."
                        }
                    ],
                    max_tokens=300
                )
                # Parse response for additional insights
                content = response.choices[0].message.content
                # Extract additional labels from response
                labels = self._extract_labels_from_text(content)
            except Exception as e:
                print(f"⚠️ Error en análisis de texto con OpenAI: {e}")
                labels = keywords
        else:
            labels = keywords
        
        return AssetAnalysis(
            asset_id=asset_id,
            asset_type=AssetType.TEXT,
            labels=labels,
            keywords=keywords,
            topics=topics,
            sentiment=sentiment,
            file_size=len(text_content.encode('utf-8'))
        )
    
    def _extract_key_frames(self, video_path: str, asset_id: str, num_frames: int = 5) -> List[str]:
        """Extract key frames from video"""
        cap = cv2.VideoCapture(video_path)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        key_frames = []
        frame_interval = max(1, frame_count // num_frames)
        
        frames_dir = self.storage_path / "frames" / asset_id
        frames_dir.mkdir(parents=True, exist_ok=True)
        
        frame_idx = 0
        saved_count = 0
        
        while cap.isOpened() and saved_count < num_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % frame_interval == 0:
                frame_path = frames_dir / f"frame_{saved_count:04d}.jpg"
                cv2.imwrite(str(frame_path), frame)
                key_frames.append(str(frame_path))
                saved_count += 1
            
            frame_idx += 1
        
        cap.release()
        return key_frames
    
    def _basic_image_analysis(self, img_path: str) -> List[str]:
        """Basic image analysis using OpenCV"""
        img = cv2.imread(img_path)
        if img is None:
            return []
        
        # Basic color analysis
        labels = []
        
        # Convert to HSV for color analysis
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Detect dominant colors
        if np.mean(hsv[:, :, 2]) > 200:
            labels.append("bright")
        elif np.mean(hsv[:, :, 2]) < 50:
            labels.append("dark")
        
        # Detect if image has high contrast
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        contrast = gray.std()
        if contrast > 50:
            labels.append("high-contrast")
        
        return labels
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text (simplified)"""
        # Basic keyword extraction
        import re
        words = re.findall(r'\b\w+\b', text.lower())
        # Filter common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [w for w in words if w not in stop_words and len(w) > 3]
        # Return top keywords
        from collections import Counter
        return [word for word, count in Counter(keywords).most_common(10)]
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from text (simplified)"""
        # Basic topic extraction - in production use NLP libraries
        topics = []
        text_lower = text.lower()
        
        topic_keywords = {
            "technology": ["tech", "software", "digital", "app", "platform"],
            "fashion": ["style", "fashion", "clothing", "wear"],
            "food": ["food", "restaurant", "recipe", "cooking"],
            "travel": ["travel", "trip", "vacation", "destination"],
            "health": ["health", "fitness", "wellness", "medical"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                topics.append(topic)
        
        return topics
    
    def _analyze_sentiment(self, text: str) -> str:
        """Basic sentiment analysis (simplified)"""
        positive_words = ["great", "excellent", "amazing", "wonderful", "best", "love", "happy"]
        negative_words = ["bad", "terrible", "awful", "worst", "hate", "sad", "disappointed"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _extract_labels_from_text(self, text: str) -> List[str]:
        """Extract labels from AI response"""
        import re
        # Look for list patterns
        labels = re.findall(r'["\']([^"\']+)["\']', text)
        return labels[:10]  # Return top 10
    
    def _download_file(self, url: str, asset_id: str, file_type: str) -> str:
        """Download file from URL (simplified)"""
        import requests
        response = requests.get(url)
        ext = url.split('.')[-1] if '.' in url else file_type
        file_path = self.storage_path / f"{asset_id}.{ext}"
        file_path.write_bytes(response.content)
        return str(file_path)
