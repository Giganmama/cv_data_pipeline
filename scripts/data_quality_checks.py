#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Quality Module
Validates video files and extracted frames
"""

import cv2
import os
import logging
from pathlib import Path
from typing import List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataQualityChecker:
    """Validates integrity and quality of CV data"""
    
    def __init__(self, min_width: int = 640, min_height: int = 480):
        self.min_width = min_width
        self.min_height = min_height
    
    def check_video_integrity(self, video_path: str) -> bool:
        """Check if video file is readable and has video stream"""
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                logger.warning(f"Cannot open video: {video_path}")
                return False
            
            # Try to read a few frames
            success = False
            for _ in range(5):
                ret, _ = cap.read()
                if ret:
                    success = True
                    break
            
            cap.release()
            
            if success:
                logger.info(f"✅ Video integrity OK: {video_path}")
                return True
            else:
                logger.warning(f"❌ Video stream empty/corrupt: {video_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking {video_path}: {e}")
            return False
    
    def check_frame_quality(self, frame_path: str) -> bool:
        """Check if image is readable and meets resolution requirements"""
        try:
            img = cv2.imread(str(frame_path))
            if img is None:
                logger.warning(f"❌ Corrupt image (cannot read): {frame_path}")
                return False
            
            h, w = img.shape[:2]
            if w < self.min_width or h < self.min_height:
                logger.warning(f"❌ Low resolution ({w}x{h}): {frame_path}")
                return False
            
            # Check for excessive black pixels (corruption indicator)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if cv2.countNonZero(gray) < 100:  # Almost completely black
                logger.warning(f"❌ Mostly black frame: {frame_path}")
                return False
            
            logger.info(f"✅ Frame quality OK: {frame_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking {frame_path}: {e}")
            return False
    
    def audit_directory(self, dir_path: str) -> Tuple[int, int]:
        """Audit all frames in directory. Returns (passed, failed) count."""
        passed = 0
        failed = 0
        dir_path = Path(dir_path)
        
        for frame_path in dir_path.glob("*.jpg"):
            if self.check_frame_quality(str(frame_path)):
                passed += 1
            else:
                failed += 1
                # Optional: Move to quarantine
                # quarantine_path = dir_path.parent / "quarantine" / frame_path.name
                # os.rename(frame_path, quarantine_path)
        
        total = passed + failed
        if total == 0:
            return 0, 0
            
        quality_pct = (passed / total) * 100
        logger.info(f" Audit Results: {passed}/{total} passed ({quality_pct:.1f}%)")
        return passed, failed

if __name__ == "__main__":
    checker = DataQualityChecker()
    checker.audit_directory("output/frames")
