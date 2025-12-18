"""
Visual Generator Service
Generates visual variations from user assets
"""
from typing import List, Dict, Any, Optional
import uuid
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    print("⚠️ OpenCV (cv2) no disponible. Algunas funcionalidades de procesamiento de video estarán deshabilitadas.")

try:
    from diffusers import StableDiffusionPipeline, ControlNetModel
    from diffusers.utils import load_image
    DIFFUSERS_AVAILABLE = True
except ImportError:
    DIFFUSERS_AVAILABLE = False
    print("⚠️ Diffusers no disponible. Instala con: pip install diffusers")

from ..models.schemas import AssetAnalysis, CreativeGeneration, AssetType


class VisualGenerator:
    """Generates visual variations from user assets"""
    
    def __init__(self, storage_path: str = "./assets/creatives"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Ad format dimensions (width, height)
        self.formats = {
            "1:1": (1080, 1080),      # Square (Instagram)
            "4:5": (1080, 1350),      # Vertical (Instagram Stories)
            "9:16": (1080, 1920),     # Full vertical (Stories)
            "16:9": (1920, 1080),     # Landscape (Facebook)
            "4:3": (1200, 900),       # Standard
        }
    
    def generate_visuals_from_asset(
        self,
        asset_analysis: AssetAnalysis,
        asset_path: str,
        options: Optional[Dict[str, Any]] = None
    ) -> List[CreativeGeneration]:
        """
        Generate visual variations from asset
        
        Args:
            asset_analysis: Analysis results
            asset_path: Path to original asset
            options: Generation options (formats, styles, etc.)
            
        Returns:
            List of CreativeGeneration objects with visual variations
        """
        if options is None:
            options = {}
        
        formats = options.get("formats", ["1:1", "4:5", "16:9"])
        add_text_overlay = options.get("add_text_overlay", False)
        text_content = options.get("text_content", None)
        
        visuals = []
        
        if asset_analysis.asset_type == AssetType.IMAGE:
            visuals = self._generate_from_image(
                asset_path,
                asset_analysis,
                formats,
                add_text_overlay,
                text_content
            )
        elif asset_analysis.asset_type == AssetType.VIDEO:
            visuals = self._generate_from_video(
                asset_path,
                asset_analysis,
                formats,
                add_text_overlay,
                text_content
            )
        
        return visuals
    
    def _generate_from_image(
        self,
        image_path: str,
        asset_analysis: AssetAnalysis,
        formats: List[str],
        add_text_overlay: bool,
        text_content: Optional[str]
    ) -> List[CreativeGeneration]:
        """Generate variations from image"""
        visuals = []
        
        # Load original image
        original_img = Image.open(image_path)
        
        for format_name in formats:
            if format_name not in self.formats:
                continue
            
            target_size = self.formats[format_name]
            
            # Resize and crop to format
            resized_img = self._resize_and_crop(original_img, target_size)
            
            # Add text overlay if requested
            if add_text_overlay and text_content:
                resized_img = self._add_text_overlay(resized_img, text_content)
            
            # Save variation
            creative_id = str(uuid.uuid4())
            output_path = self.storage_path / f"{creative_id}_{format_name}.jpg"
            resized_img.save(output_path, quality=95)
            
            creative = CreativeGeneration(
                creative_id=creative_id,
                asset_id=asset_analysis.asset_id,
                creative_type="visual",
                visual_url=str(output_path),
                format=format_name,
                generation_params={
                    "format": format_name,
                    "has_text_overlay": add_text_overlay
                }
            )
            visuals.append(creative)
        
        return visuals
    
    def _generate_from_video(
        self,
        video_path: str,
        asset_analysis: AssetAnalysis,
        formats: List[str],
        add_text_overlay: bool,
        text_content: Optional[str]
    ) -> List[CreativeGeneration]:
        """Generate variations from video (extract frames and create clips)"""
        visuals = []
        
        # Extract key frames
        if not CV2_AVAILABLE:
            # Fallback sin cv2: usar metadata básica
            return {
                "fps": 30.0,
                "frame_count": 0,
                "duration": 0.0,
                "keyframes": []
            }
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Extract frames at intervals
        frame_interval = max(1, frame_count // 5)  # 5 frames
        
        frame_idx = 0
        extracted_frames = []
        
        while cap.isOpened() and len(extracted_frames) < 5:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % frame_interval == 0:
                # Convert BGR to RGB
                if CV2_AVAILABLE:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                else:
                    # Fallback: convertir usando PIL
                    frame_rgb = Image.fromarray(frame).convert('RGB')
                frame_img = Image.fromarray(frame_rgb)
                extracted_frames.append(frame_img)
            
            frame_idx += 1
        
        cap.release()
        
        # Generate visuals from extracted frames
        for i, frame_img in enumerate(extracted_frames):
            for format_name in formats[:2]:  # Limit formats for videos
                if format_name not in self.formats:
                    continue
                
                target_size = self.formats[format_name]
                resized_img = self._resize_and_crop(frame_img, target_size)
                
                if add_text_overlay and text_content:
                    resized_img = self._add_text_overlay(resized_img, text_content)
                
                creative_id = str(uuid.uuid4())
                output_path = self.storage_path / f"{creative_id}_{format_name}_frame{i}.jpg"
                resized_img.save(output_path, quality=95)
                
                creative = CreativeGeneration(
                    creative_id=creative_id,
                    asset_id=asset_analysis.asset_id,
                    creative_type="visual",
                    visual_url=str(output_path),
                    format=format_name,
                    generation_params={
                        "format": format_name,
                        "source_frame": i,
                        "has_text_overlay": add_text_overlay
                    }
                )
                visuals.append(creative)
        
        return visuals
    
    def _resize_and_crop(self, img: Image.Image, target_size: tuple) -> Image.Image:
        """Resize and crop image to target size maintaining aspect ratio"""
        target_w, target_h = target_size
        img_w, img_h = img.size
        
        # Calculate scaling
        scale = max(target_w / img_w, target_h / img_h)
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        
        # Resize
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Crop to target size (center crop)
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        right = left + target_w
        bottom = top + target_h
        
        cropped = resized.crop((left, top, right, bottom))
        
        return cropped
    
    def _add_text_overlay(self, img: Image.Image, text: str) -> Image.Image:
        """Add text overlay to image"""
        draw = ImageDraw.Draw(img)
        
        # Try to load a font
        try:
            # Try to use a system font
            font_size = 60
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
                except:
                    font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # Calculate text position (bottom center)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        img_w, img_h = img.size
        x = (img_w - text_w) // 2
        y = img_h - text_h - 50
        
        # Draw text with background
        padding = 10
        draw.rectangle(
            [x - padding, y - padding, x + text_w + padding, y + text_h + padding],
            fill=(0, 0, 0, 180)  # Semi-transparent black
        )
        draw.text((x, y), text, fill=(255, 255, 255), font=font)
        
        return img


