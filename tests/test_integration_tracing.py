"""Integration tests for tracing through the full auto_process pipeline."""

import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gizli_maskele
from gizli_maskele import reset_trace_context, start_span, end_span, get_traces, get_trace_id


def test_auto_process_creates_trace():
    """Test that auto_process would create a trace when run."""
    # We can't easily run the full auto_process without dependencies,
    # but we can test the tracing integration points
    
    # Reset context to simulate fresh run
    reset_trace_context()
    
    # Simulate what auto_process.py does in its main() function
    main_span_id = start_span("auto_process_main")
    
    # Verify we have a trace
    trace_id = get_trace_id()
    assert trace_id is not None
    assert isinstance(trace_id, str)
    assert len(trace_id) > 0
    
    # Verify we have the main span
    current_span = get_current_span_id()
    assert current_span == main_span_id
    
    # Simulate some work
    project_span = start_span("process_project", main_span_id)
    # ... would do project work ...
    end_span(project_span)
    
    # End main span
    end_span(main_span_id)
    
    # Verify trace data
    traces = get_traces()
    assert traces['trace_id'] == trace_id
    assert len(traces['spans']) == 2  # main and project spans
    
    # Check span hierarchy
    span_map = {span['span_id']: span for span in traces['spans']}
    assert span_map[main_span_id]['operation_name'] == "auto_process_main"
    assert span_map[project_span]['operation_name'] == "process_project"
    assert span_map[project_span]['parent_span_id'] == main_span_id


def test_trace_context_isolation_between_runs():
    """Test that trace contexts are isolated between different runs."""
    # First run
    reset_trace_context()
    first_main_span = start_span("auto_process_main")
    first_trace_id = get_trace_id()
    end_span(first_main_span)
    
    # Second run
    reset_trace_context()
    second_main_span = start_span("auto_process_main")
    second_trace_id = get_trace_id()
    end_span(second_main_span)
    
    # Should have different trace IDs
    assert first_trace_id != second_trace_id
    
    # Each should have their own spans
    first_traces = get_traces()
    second_traces = get_traces()
    
    assert len(first_traces['spans']) == 1
    assert len(second_traces['spans']) == 1
    assert first_traces['spans'][0]['operation_name'] == "auto_process_main"
    assert second_traces['spans'][0]['operation_name'] == "auto_process_main"


def test_nested_operation_tracing():
    """Test tracing of nested operations as would occur in auto_process."""
    reset_trace_context()
    
    # Simulate the structure we see in auto_process.py
    main_span = start_span("auto_process_main")
    
    # Simulate project processing loop
    project_span = start_span("process_project", main_span)
    
    # Simulate render phase
    render_span = start_span("render_video", project_span)
    # ... render work ...
    end_span(render_span)
    
    # Simulate upload phases
    youtube_span = start_span("upload_youtube", project_span)
    # ... youtube work ...
    end_span(youtube_span)
    
    instagram_span = start_span("upload_instagram", project_span)
    # ... instagram work ...
    end_span(instagram_span)
    
    # End project and main
    end_span(project_span)
    end_span(main_span)
    
    # Verify trace structure
    traces = get_traces()
    assert len(traces['spans']) == 5  # main, project, render, youtube, instagram
    
    # Build lookup
    spans_by_id = {span['span_id']: span for span in traces['spans']}
    
    # Verify hierarchy
    assert spans_by_id[project_span]['parent_span_id'] == main_span
    assert spans_by_id[render_span]['parent_span_id'] == project_span
    assert spans_by_id[youtube_span]['parent_span_id'] == project_span
    assert spans_by_id[instagram_span]['parent_span_id'] == project_span
    
    # Verify operation names
    assert spans_by_id[main_span]['operation_name'] == "auto_process_main"
    assert spans_by_id[project_span]['operation_name'] == "process_project"
    assert spans_by_id[render_span]['operation_name'] == "render_video"
    assert spans_by_id[youtube_span]['operation_name'] == "upload_youtube"
    assert spans_by_id[instagram_span]['operation_name'] == "upload_instagram"


def test_trace_persistence_in_logs():
    """Test that trace information would persist in json_log output."""
    reset_trace_context()
    
    # Create a span
    span_id = start_span("test_operation")
    
    # Capture json_log output
    import io
    import json
    import sys
    
    old_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()
    
    try:
        # Log something with trace context
        gizli_maskele.json_log("Test log message", project="test", value=123)
        
        # Get output
        output = captured_output.getvalue().strip()
        log_entry = json.loads(output)
        
        # Verify trace context is included
        assert log_entry["trace_id"] == get_trace_id()
        assert log_entry["span_id"] == span_id
        assert log_entry["message"] == "Test log message"
        assert log_entry["project"] == "test"
        assert log_entry["value"] == 123
        
    finally:
        sys.stdout = old_stdout


def test_trace_cleanup_on_exception():
    """Test that trace context is properly cleaned up even if exceptions occur."""
    reset_trace_context()
    
    main_span_id = start_span("auto_process_main")
    
    try:
        # Simulate some work that fails
        project_span = start_span("process_project", main_span_id)
        # Simulate an error
        raise ValueError("Simulated error")
    except ValueError:
        # Error handled
        pass
    finally:
        # This is what auto_process.py does in its finally block
        if 'main_span_id' in locals():
            end_span(main_span_id)
    
    # Verify trace still captured the work despite exception
    traces = get_traces()
    assert len(traces['spans']) == 2  # main and project spans
    
    # Verify both spans were ended
    ctx = get_trace_context()
    for span in ctx.spans:
        assert span['end_time'] is not None


if __name__ == "__main__":
    # Run tests if executed directly
    import pytest
    pytest.main([__file__, "-v"])