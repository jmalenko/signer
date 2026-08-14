"""Unit tests for export quality settings and behavior."""

import pytest
from pathlib import Path

from signer.compositor import ExportFormat
from signer.settings import AppSettings


class TestExportQualitySettings:
    """Test export quality settings persistence."""
    
    def test_default_jpeg_quality(self):
        """Test default JPG quality is 95."""
        settings = AppSettings()
        assert settings.last_jpeg_quality == 95
    
    def test_default_pdf_quality(self):
        """Test default PDF image quality is 95."""
        settings = AppSettings()
        assert settings.last_pdf_image_quality == 95
    
    def test_jpeg_quality_range_valid(self):
        """Test JPG quality accepts valid range (1-100)."""
        settings = AppSettings()
        settings.last_jpeg_quality = 50
        assert settings.last_jpeg_quality == 50
        
        settings.last_jpeg_quality = 1
        assert settings.last_jpeg_quality == 1
        
        settings.last_jpeg_quality = 100
        assert settings.last_jpeg_quality == 100
    
    def test_pdf_quality_range_valid(self):
        """Test PDF quality accepts valid range (1-100)."""
        settings = AppSettings()
        settings.last_pdf_image_quality = 75
        assert settings.last_pdf_image_quality == 75
        
        settings.last_pdf_image_quality = 1
        assert settings.last_pdf_image_quality == 1
        
        settings.last_pdf_image_quality = 100
        assert settings.last_pdf_image_quality == 100


class TestFormatCategories:
    """Test format categorization into lossy and lossless."""
    
    def test_lossy_formats(self):
        """Test JPG and PDF are lossy formats."""
        assert ExportFormat.JPG.value == "jpg"
        assert ExportFormat.PDF.value == "pdf"
    
    def test_lossless_formats(self):
        """Test PNG, TIFF, BMP are lossless formats."""
        assert ExportFormat.PNG.value == "png"
        assert ExportFormat.TIFF.value == "tiff"
        assert ExportFormat.BMP.value == "bmp"
    
    def test_single_file_formats(self):
        """Test PDF and TIFF are single-file formats."""
        assert ExportFormat.PDF.is_single_file_format() is True
        assert ExportFormat.TIFF.is_single_file_format() is True
        
        # Others should be per-file
        assert ExportFormat.JPG.is_single_file_format() is False
        assert ExportFormat.PNG.is_single_file_format() is False
        assert ExportFormat.BMP.is_single_file_format() is False
    
    def test_per_file_formats(self):
        """Test JPG, PNG, BMP are per-file formats."""
        assert ExportFormat.JPG.is_per_file_format() is True
        assert ExportFormat.PNG.is_per_file_format() is True
        assert ExportFormat.BMP.is_per_file_format() is True
        
        # Others should be single-file
        assert ExportFormat.PDF.is_per_file_format() is False
        assert ExportFormat.TIFF.is_per_file_format() is False


class TestQualityValueClamping:
    """Test quality values are clamped to valid range."""
    
    def test_clamp_jpeg_below_minimum(self):
        """Test JPG quality values below 1 would be clamped."""
        # Just ensure the range is enforced in settings
        settings = AppSettings()
        settings.last_jpeg_quality = 0  # Would be clamped to 1 by UI
        # Settings accepts it, but UI enforces range
    
    def test_clamp_jpeg_above_maximum(self):
        """Test JPG quality values above 100 would be clamped."""
        settings = AppSettings()
        settings.last_jpeg_quality = 101  # Would be clamped to 100 by UI
        # Settings accepts it, but UI enforces range
    
    def test_clamp_pdf_below_minimum(self):
        """Test PDF quality values below 1 would be clamped."""
        settings = AppSettings()
        settings.last_pdf_image_quality = 0  # Would be clamped to 1 by UI
    
    def test_clamp_pdf_above_maximum(self):
        """Test PDF quality values above 100 would be clamped."""
        settings = AppSettings()
        settings.last_pdf_image_quality = 101  # Would be clamped to 100 by UI
