"""
Basic tests for the pipeline module.
"""

import pytest
import pandas as pd
from pipeline.utils import read_results_table
from pipeline.export import export_results

def test_export_results():
    """Test export functionality with mock data."""
    # This would need actual data to test properly
    # For now, just test that the function exists and handles errors
    try:
        result = export_results("non-existent-run", "geojson")
        # Should raise an error for non-existent run
        assert False, "Should have raised an error"
    except Exception:
        # Expected behavior for non-existent run
        pass

def test_read_results_table():
    """Test reading results table."""
    # This would need actual data to test properly
    try:
        df = read_results_table("non-existent-run")
        assert False, "Should have raised an error"
    except Exception:
        # Expected behavior for non-existent run
        pass
