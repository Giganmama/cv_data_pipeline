#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Metadata Extractor
Collects technical details about video files for dataset organization
"""

import os
import json
import logging
import ffmpeg
import subprocess
from pathlib import Path
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetadataExtractor:
    """Extracts technical metadata from video files"""
    
    def extract(self, video_path: str) -> Dict[str, Any]:
        """Extract comprehensive metadata"""
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        logger.info(f"Extracting metadata for {video_path}")
        
        try:
            probe = ffmpeg.probe(str(video_path))
            video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
            
            # Basic file info
            stat = os.stat(video_path)
            
            metadata = {
                "file_name": video_path.name,
                "file_size_mb": round(stat.st_size / (1024 * 1024), 2),
                "duration_sec": float(video_stream.get('duration', 0)),
                "format": probe['format']['format_name'],
                "video": {
                    "codec": video_stream.get('codec_name'),
                    "width": int(video_stream.get('width', 0)),
                    "height": int(video_stream.get('height', 0)),
                    "fps": eval(video_stream.get('avg_frame_rate', '0/1')),
                    "bitrate_kbps": round(int(video_stream.get('bit_rate', 0)) / 1000, 2),
                    "color_space": video_stream.get('pix_fmt')
                },
                "audio": {
                    "codec": audio_stream.get('codec_name') if audio_stream else None,
                    "sample_rate": int(audio_stream.get('sample_rate', 0)) if audio_stream else 0,
                    "channels": int(audio_stream.get('channels', 0)) if audio_stream else 0
                }
            }
            
            # Save metadata to JSON sidecar
            output_path = video_path.with_suffix('.json')
            with open(output_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Metadata saved to {output_path}")
            return metadata
            
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg probe error: {e.stderr.decode()}")
            return {}

if __name__ == "__main__":
    extractor = MetadataExtractor()
    meta = extractor.extract("test_video.mp4")
    print(json.dumps(meta, indent=2))
