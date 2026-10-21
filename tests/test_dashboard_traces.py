"""Tests for dashboard trace visualization functionality."""

import dashboard
from unittest.mock import patch, MagicMock
import gizli_maskele
from gizli_maskele import reset_trace_context, start_span, end_span, get_traces


def test_dashboard_imports():
    """Test that dashboard imports successfully."""
    assert dashboard is not None


def test_trace_visualization_section_exists():
    """Test that dashboard has trace visualization logic."""
    # We can't easily test the full streamlit rendering without running it,
    # but we can test that the import and basic structure works
    
    # Test that we can access the tracing functions from dashboard context
    assert hasattr(gizli_maskele, 'get_traces')
    assert hasattr(gizli_maskele, 'reset_trace_context')
    assert hasattr(gizli_maskele, 'start_span')
    assert hasattr(gizli_maskele, 'end_span')


def test_trace_data_structure_for_dashboard():
    """Test that trace data has the structure expected by dashboard."""
    reset_trace_context()
    
    # Create some test spans
    root_id = start_span("root_operation")
    child_id = start_span("child_operation", root_id)
    end_span(child_id)
    end_span(root_id)
    
    # Get traces as dashboard would
    traces = get_traces()
    
    # Verify structure matches what dashboard expects
    assert 'trace_id' in traces
    assert 'spans' in traces
    assert isinstance(traces['trace_id'], str)
    assert len(traces['trace_id']) > 0
    assert isinstance(traces['spans'], list)
    
    # Check each span has required fields for dashboard display
    for span in traces['spans']:
        assert 'span_id' in span
        assert 'parent_span_id' in span
        assert 'operation_name' in span
        assert 'start_time' in span
        assert 'end_time' in span
        assert isinstance(span['span_id'], str)
        assert isinstance(span['operation_name'], str)
        assert isinstance(span['start_time'], float)
        assert span['end_time'] is None or isinstance(span['end_time'], float)


def test_empty_trace_handling():
    """Test handling of empty or missing trace data."""
    reset_trace_context()
    
    # Clear trace context to simulate no trace
    if hasattr(gizli_maskele._trace_context, 'trace_id'):
        delattr(gizli_maskele._trace_context, 'trace_id')
    if hasattr(gizli_maskele._trace_context, 'span_id'):
        delattr(gizli_maskele._trace_context, 'span_id')
    
    traces = get_traces()
    
    # Should still return valid structure
    assert isinstance(traces, dict)
    assert 'trace_id' in traces
    assert 'spans' in traces
    assert traces['trace_id'] is None
    assert isinstance(traces['spans'], list)
    assert len(traces['spans']) == 0


def test_span_duration_calculation():
    """Test that span durations are calculated correctly for dashboard."""
    reset_trace_context()
    
    start_time = 1000.0
    end_time = 1005.5  # 5.5 seconds later
    
    # Mock time to control timing
    import time
    original_time = time.time
    
    def mock_time():
        return start_time
    
    with patch('time.time', side_effect=[start_time, start_time + 2.0, end_time]):
        span_id = start_span("timed_operation")
        time.sleep(0.001)  # Small sleep to avoid same timestamp
        end_span(span_id)
    
    traces = get_traces()
    assert len(traces['spans']) == 1
    
    span = traces['spans'][0]
    duration = span['end_time'] - span['start_time']
    
    # Should be approximately 5.5 seconds
    assert 5.0 <= duration <= 6.0, f"Duration {duration} not in expected range"


def test_span_hierarchy_display():
    """Test that span hierarchy is preserved for dashboard display."""
    reset_trace_context()
    
    # Create hierarchy: A -> B -> C
    a_id = start_span("Operation_A")
    b_id = start_span("Operation_B", a_id)
    c_id = start_span("Operation_C", b_id)
    
    end_span(c_id)
    end_span(b_id)
    end_span(a_id)
    
    traces = get_traces()
    assert len(traces['spans']) == 3
    
    # Build span lookup
    spans_by_id = {span['span_id']: span for span in traces['spans']}
    
    # Verify hierarchy
    assert spans_by_id[a_id]['parent_span_id'] is None or spans_by_id[a_id]['parent_span_id'] == ""
    assert spans_by_id[b_id]['parent_span_id'] == a_id
    assert spans_by_id[c_id]['parent_span_id'] == b_id
    
    # Verify operation names
    assert spans_by_id[a_id]['operation_name'] == "Operation_A"
    assert spans_by_id[b_id]['operation_name'] == "Operation_B"
    assert spans_by_id[c_id]['operation_name'] == "Operation_C"


def test_dashboard_trace_section_logic():
    """Test the logic that would be used in dashboard trace section."""
    reset_trace_context()
    
    # Create test data
    root_id = start_span("auto_process_main")
    project_id = start_span("process_project", root_id)
    render_id = start_span("render_video", project_id)
    end_span(render_id)
    upload_id = start_span("upload_youtube", project_id)
    end_span(upload_id)
    end_span(project_id)
    end_span(root_id)
    
    # Simulate dashboard logic
    traces = get_traces()
    
    # Dashboard shows trace ID
    assert traces['trace_id'] is not None
    
    # Dashboard shows span table
    span_data = []
    for span in traces['spans']:
        duration = span['end_time'] - span['start_time'] if span['end_time'] else 0
        span_data.append({
            "İşlem": span['operation_name'],
            "Span ID": span['span_id'],
            "Üst Span": span['parent_span_id'] or "Ana",
            "Süre (sn)": f"{duration:.3f}"
        })
    
    # Should have data for all spans
    assert len(span_data) == 4  # root, project, render, upload
    
    # Check specific spans are present
    operations = [item["İşlem"] for item in span_data]
    assert "auto_process_main" in operations
    assert "process_project" in operations
    assert "render_video" in operations
    assert "upload_youtube" in operations
    
    # Check hierarchy relationships
    span_dict = {item["Span ID"]: item for item in span_data}
    assert span_dict[project_id]["Üst Span"] == span_dict[root_id]["Span ID"]
    assert span_dict[render_id]["Üst Span"] == span_dict[project_id]["Span ID"]
    assert span_dict[upload_id]["Üst Span"] == span_dict[project_id]["Span ID"]


if __name__ == "__main__":
    # Run tests if executed directly
    import pytest
    pytest.main([__file__, "-v"])