"""
Verificación biométrica usando Face++ o AWS Rekognition.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from pathlib import Path

try:
    import boto3
    AWS_REKOGNITION_AVAILABLE = True
except ImportError:
    AWS_REKOGNITION_AVAILABLE = False
    logging.warning("boto3 no disponible para AWS Rekognition")

try:
    import facepp
    FACEPP_AVAILABLE = True
except ImportError:
    FACEPP_AVAILABLE = False
    logging.warning("facepp no disponible")

logger = logging.getLogger(__name__)


class BiometricVerification:
    """Verificación biométrica para match de fotos con documentos de identidad."""
    
    def __init__(self, provider: str = "aws", api_key: Optional[str] = None):
        self.provider = provider
        self.api_key = api_key
        
        if provider == "aws" and AWS_REKOGNITION_AVAILABLE:
            self.rekognition = boto3.client('rekognition')
        elif provider == "facepp" and FACEPP_AVAILABLE and api_key:
            self.facepp_client = facepp.API(api_key=api_key)
        else:
            self.rekognition = None
            self.facepp_client = None
    
    def verify_face_match(
        self,
        id_photo_path: str,
        selfie_path: str,
        threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        Verifica si una selfie coincide con la foto del documento de identidad.
        
        Args:
            id_photo_path: Ruta a foto del DNI/pasaporte
            selfie_path: Ruta a selfie del cliente
            threshold: Umbral de confianza (0.0-1.0)
        
        Returns:
            Dict con match_result, confidence, etc.
        """
        try:
            if self.provider == "aws" and self.rekognition:
                return self._verify_aws_rekognition(id_photo_path, selfie_path, threshold)
            elif self.provider == "facepp" and self.facepp_client:
                return self._verify_facepp(id_photo_path, selfie_path, threshold)
            else:
                return {
                    "success": False,
                    "error": "Provider no disponible"
                }
        except Exception as e:
            logger.error(f"Error en verificación biométrica: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _verify_aws_rekognition(
        self,
        id_photo_path: str,
        selfie_path: str,
        threshold: float
    ) -> Dict[str, Any]:
        """Verificación usando AWS Rekognition."""
        try:
            with open(id_photo_path, 'rb') as id_photo, open(selfie_path, 'rb') as selfie:
                id_bytes = id_photo.read()
                selfie_bytes = selfie.read()
            
            response = self.rekognition.compare_faces(
                SourceImage={'Bytes': id_bytes},
                TargetImage={'Bytes': selfie_bytes},
                SimilarityThreshold=threshold * 100
            )
            
            if response['FaceMatches']:
                similarity = response['FaceMatches'][0]['Similarity'] / 100.0
                return {
                    "success": True,
                    "match": True,
                    "confidence": similarity,
                    "threshold": threshold
                }
            else:
                return {
                    "success": True,
                    "match": False,
                    "confidence": 0.0,
                    "threshold": threshold
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _verify_facepp(
        self,
        id_photo_path: str,
        selfie_path: str,
        threshold: float
    ) -> Dict[str, Any]:
        """Verificación usando Face++."""
        try:
            # Face++ API call
            result = self.facepp_client.compare(
                image_file1=Path(id_photo_path),
                image_file2=Path(selfie_path)
            )
            
            confidence = result.get("confidence", 0.0) / 100.0
            match = confidence >= threshold
            
            return {
                "success": True,
                "match": match,
                "confidence": confidence,
                "threshold": threshold
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

