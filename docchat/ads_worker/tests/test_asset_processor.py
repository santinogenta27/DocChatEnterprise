"""
Tests for Asset Processor
"""
import pytest
from pathlib import Path
import tempfile
from PIL import Image
import numpy as np

from ..services.asset_processor import AssetProcessor
from ..models.schemas import AssetType


@pytest.fixture
def asset_processor():
    """Create AssetProcessor instance for testing"""
    return AssetProcessor(openai_api_key=None, storage_path=str(Path(tempfile.mkdtemp())))


@pytest.fixture
def sample_image():
    """Create a sample test image"""
    img = Image.new('RGB', (100, 100), color='red')
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    img.save(temp_file.name)
    return temp_file.name


def test_process_image(asset_processor, sample_image):
    """Test image processing"""
    analysis = asset_processor.process_asset(
        AssetType.IMAGE,
        file_path=sample_image,
        file_url=None,
        text_content=None,
        metadata=None
    )
    
    assert analysis.asset_type == AssetType.IMAGE
    assert analysis.asset_id is not None
    assert analysis.resolution is not None


def test_process_text(asset_processor):
    """Test text processing"""
    text_content = "Amazing product for sale! Best quality and great prices."
    
    analysis = asset_processor.process_asset(
        AssetType.TEXT,
        file_path=None,
        file_url=None,
        text_content=text_content,
        metadata=None
    )
    
    assert analysis.asset_type == AssetType.TEXT
    assert analysis.asset_id is not None
    assert len(analysis.keywords) > 0

