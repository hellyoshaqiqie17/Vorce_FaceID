import cv2
import numpy as np
import base64
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from src.face_detector import FaceDetector
from src.blink_detector import BlinkDetector


@dataclass
class LivenessResult:
    is_real: bool
    confidence: float
    checks: Dict[str, any]
    details: Dict[str, any]


class LivenessService:
    def __init__(self):
        self.face_detector = FaceDetector()
        self.blink_detector = BlinkDetector()
        
        self.pose_thresholds = {
            'right': {'yaw_min': 15, 'yaw_max': 100},
            'left': {'yaw_min': -100, 'yaw_max': -15},
            'up': {'pitch_min': -100, 'pitch_max': -10},
            'down': {'pitch_min': 20, 'pitch_max': 100},
            'center': {'yaw_min': -15, 'yaw_max': 15, 'pitch_min': -10, 'pitch_max': 20}
        }
    
    def decode_base64(self, base64_str: str) -> Optional[np.ndarray]:
        try:
            img_data = base64.b64decode(base64_str)
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            print(f"Decode error: {e}")
            return None
    
    def validate_pose(self, frame_b64: str, expected_pose: str) -> Dict[str, any]:
        frame = self.decode_base64(frame_b64)
        if frame is None:
            return {
                'valid': False,
                'expected': expected_pose,
                'actual': 'decode_error',
                'confidence': 0.0,
                'error': 'Failed to decode image'
            }
        
        result = self.face_detector.detect(frame)
        
        if not result.face_detected:
            return {
                'valid': False,
                'expected': expected_pose,
                'actual': 'no_face',
                'confidence': 0.0,
                'error': result.error or 'No face detected'
            }
        
        if not result.head_pose:
            return {
                'valid': False,
                'expected': expected_pose,
                'actual': 'no_pose',
                'confidence': 0.0,
                'error': 'Head pose not detected'
            }
        
        pose = result.head_pose
        thresholds = self.pose_thresholds.get(expected_pose, {})
        
        is_valid = False
        confidence = 0.0
        
        if expected_pose in ['right', 'left']:
            yaw_min = thresholds.get('yaw_min', 0)
            yaw_max = thresholds.get('yaw_max', 0)
            is_valid = yaw_min <= pose.yaw <= yaw_max
            
            if is_valid:
                mid = (yaw_min + yaw_max) / 2
                distance = abs(pose.yaw - mid)
                max_distance = abs(yaw_max - mid)
                confidence = max(0.0, 1.0 - (distance / max_distance))
            
        elif expected_pose in ['up', 'down']:
            pitch_min = thresholds.get('pitch_min', 0)
            pitch_max = thresholds.get('pitch_max', 0)
            is_valid = pitch_min <= pose.pitch <= pitch_max
            
            if is_valid:
                mid = (pitch_min + pitch_max) / 2
                distance = abs(pose.pitch - mid)
                max_distance = abs(pitch_max - mid)
                confidence = max(0.0, 1.0 - (distance / max_distance))
        
        elif expected_pose == 'center':
            yaw_ok = thresholds['yaw_min'] <= pose.yaw <= thresholds['yaw_max']
            pitch_ok = thresholds['pitch_min'] <= pose.pitch <= thresholds['pitch_max']
            is_valid = yaw_ok and pitch_ok
            
            if is_valid:
                yaw_conf = 1.0 - (abs(pose.yaw) / 15.0)
                pitch_conf = 1.0 - (abs(pose.pitch) / 15.0)
                confidence = (yaw_conf + pitch_conf) / 2
        
        return {
            'valid': is_valid,
            'expected': expected_pose,
            'actual': pose.direction,
            'confidence': round(confidence, 3),
            'yaw': round(pose.yaw, 2),
            'pitch': round(pose.pitch, 2)
        }
    
    def validate_blink(self, frames_b64: List[str]) -> Dict[str, any]:
        self.blink_detector.reset()
        
        blink_count = 0
        frames_processed = 0
        
        for frame_b64 in frames_b64:
            frame = self.decode_base64(frame_b64)
            if frame is None:
                continue
            
            result = self.face_detector.detect(frame)
            if not result.face_detected:
                continue
            
            frames_processed += 1
            blink_result = self.blink_detector.detect(result.left_eye, result.right_eye)
            
            if blink_result and blink_result.blink_count > blink_count:
                blink_count = blink_result.blink_count
        
        is_valid = blink_count >= 1
        confidence = min(1.0, blink_count / 1.0) if is_valid else 0.0
        
        return {
            'valid': is_valid,
            'blink_count': blink_count,
            'frames_processed': frames_processed,
            'confidence': round(confidence, 3)
        }
    
    def validate_liveness(self, frames: Dict[str, any]) -> LivenessResult:
        checks = {}
        all_valid = True
        total_confidence = 0.0
        check_count = 0
        
        pose_keys = ['right', 'left', 'up', 'down', 'center']
        for pose in pose_keys:
            if pose not in frames:
                checks[f'pose_{pose}'] = {
                    'valid': False,
                    'error': 'Frame not provided'
                }
                all_valid = False
                continue
            
            result = self.validate_pose(frames[pose], pose)
            checks[f'pose_{pose}'] = result
            
            if not result['valid']:
                all_valid = False
            else:
                total_confidence += result['confidence']
                check_count += 1
        
        if 'blink' not in frames:
            checks['blink'] = {
                'valid': False,
                'error': 'Blink frames not provided'
            }
            all_valid = False
        else:
            blink_frames = frames['blink']
            if not isinstance(blink_frames, list):
                blink_frames = [blink_frames]
            
            result = self.validate_blink(blink_frames)
            checks['blink'] = result
            
            if not result['valid']:
                all_valid = False
            else:
                total_confidence += result['confidence']
                check_count += 1
        
        overall_confidence = total_confidence / check_count if check_count > 0 else 0.0
        
        face_consistency = self._check_face_consistency(frames)
        checks['face_consistency'] = face_consistency
        
        if not face_consistency['valid']:
            all_valid = False
        else:
            overall_confidence = (overall_confidence + face_consistency['confidence']) / 2
        
        return LivenessResult(
            is_real=all_valid,
            confidence=round(overall_confidence, 3),
            checks=checks,
            details={
                'total_checks': check_count + 1,
                'passed_checks': sum(1 for c in checks.values() if c.get('valid', False)),
                'anti_spoofing': {
                    'head_movement': all([checks.get(f'pose_{p}', {}).get('valid', False) for p in pose_keys]),
                    'blink_detected': checks.get('blink', {}).get('valid', False),
                    'face_consistency': face_consistency['valid']
                }
            }
        )
    
    def _check_face_consistency(self, frames: Dict[str, any]) -> Dict[str, any]:
        face_sizes = []
        
        for key, frame_data in frames.items():
            if key == 'blink':
                if isinstance(frame_data, list):
                    frame_data = frame_data[0] if frame_data else None
                else:
                    continue
            
            if not frame_data:
                continue
            
            frame = self.decode_base64(frame_data)
            if frame is None:
                continue
            
            result = self.face_detector.detect(frame)
            if result.face_detected and result.bbox:
                x, y, w, h = result.bbox
                face_sizes.append(w * h)
        
        if len(face_sizes) < 3:
            return {
                'valid': False,
                'confidence': 0.0,
                'error': 'Not enough faces detected for consistency check'
            }
        
        avg_size = np.mean(face_sizes)
        std_size = np.std(face_sizes)
        
        variation = std_size / avg_size if avg_size > 0 else 1.0
        
        is_consistent = variation < 0.3
        confidence = max(0.0, 1.0 - (variation / 0.3))
        
        return {
            'valid': is_consistent,
            'confidence': round(confidence, 3),
            'variation': round(variation, 3),
            'avg_face_size': round(avg_size, 2)
        }


liveness_service = LivenessService()
