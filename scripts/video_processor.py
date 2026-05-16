#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Processor Module
Extract frames, resize, convert formats using OpenCV + ffmpeg
"""

import os
import cv2
import ffmpeg
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoProcessor:
    """Process video files: extract frames, metadata, convert formats"""
    
    def __init__(
        self,
        output_dir: str = "output/frames",
        frame_format: str = "jpg",
        fps: Optional[int] = None,  # Extract N frames per second (None = all)
        resize: Optional[tuple] = None,  # (width, height) or None
        quality: int = 95  # JPEG quality 1-100
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.frame_format = frame_format
        self.fps = fps
        self.resize = resize
        self.quality = quality
    
    def get_video_metadata(self, video_path: str) -> dict:
        """Extract metadata using ffprobe"""
        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            
            return {
                "duration_sec": float(video_stream.get('duration', 0)),
                "fps": eval(video_stream.get('avg_frame_rate', '0/1')),
                "width": int(video_stream.get('width', 0)),
                "height": int(video_stream.get('height', 0)),
                "codec": video_stream.get('codec_name', 'unknown'),
                "bitrate": int(video_stream.get('bit_rate', 0)),
                "file_size": os.path.getsize(video_path),
                "extracted_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
            return {}
    
    def extract_frames(self, video_path: str, output_prefix: Optional[str] = None) -> List[str]:
        """Extract frames from video with optional filtering/resizing"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(video_fps / self.fps) if self.fps else 1
        
        saved_paths = []
        frame_count = 0
        saved_count = 0
        
        logger.info(f"Processing {video_path}: {total_frames} frames, extracting every {frame_interval} frame(s)")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                # Optional resize
                if self.resize:
                    frame = cv2.resize(frame, self.resize, interpolation=cv2.INTER_LANCZOS4)
                
                # Generate output path
                prefix = output_prefix or Path(video_path).stem
                output_path = self.output_dir / f"{prefix}_frame_{saved_count:06d}.{self.frame_format}"
                
                # Save with quality control
                if self.frame_format.lower() == 'jpg':
                    cv2.imwrite(str(output_path), frame, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
                else:
                    cv2.imwrite(str(output_path), frame)
                
                saved_paths.append(str(output_path))
                saved_count += 1
            
            frame_count += 1
        
        cap.release()
        logger.info(f"Extracted {saved_count} frames to {self.output_dir}")
        return saved_paths
    
    def convert_format(self, video_path: str, output_format: str = 'mp4', codec: str = 'libx265') -> str:
        """Convert video to different format/codec (e.g., h264 → h265 for compression)"""
        output_path = str(Path(video_path).with_suffix(f'.{output_format}'))
        
        try:
            ffmpeg.input(video_path).output(
                output_path,
                vcodec=codec,
                preset='slow',  # Better compression
                crf=28  # Quality factor (lower = better)
            ).run(overwrite_output=True, quiet=True)
            
            original_size = os.path.getsize(video_path)
            converted_size = os.path.getsize(output_path)
            savings = (1 - converted_size / original_size) * 100
            
            logger.info(f"Converted: {video_path} → {output_path} ({savings:.1f}% smaller)")
            return output_path
            
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error: {e.stderr.decode()}")
            raise
    
    def validate_frame(self, frame_path: str, min_size: tuple = (640, 480)) -> bool:
        """Check if frame meets quality requirements"""
        try:
            img = cv2.imread(frame_path)
            if img is None:
                return False
            h, w = img.shape[:2]
            return w >= min_size[0] and h >= min_size[1]
        except:
            return False


# CLI interface for manual testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="CV Video Processor")
    parser.add_argument("--input", required=True, help="Path to input video")
    parser.add_argument("--output", default="output/frames", help="Output directory")
    parser.add_argument("--fps", type=int, help="Frames per second to extract (default: all)")
    parser.add_argument("--resize", type=str, help="Resize to WxH (e.g., '640x480')")
    parser.add_argument("--metadata", action="store_true", help="Only extract metadata")
    
    args = parser.parse_args()
    
    processor = VideoProcessor(
        output_dir=args.output,
        fps=args.fps,
        resize=tuple(map(int, args.resize.split('x'))) if args.resize else None
    )
    
    if args.metadata:
        meta = processor.get_video_metadata(args.input)
        print(f"Metadata: {meta}")
    else:
        frames = processor.extract_frames(args.input)
        print(f"Saved {len(frames)} frames")
