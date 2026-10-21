"""Tests for distributed tracing functionality in gizli_maskele module."""

import time
import json
from unittest.mock import patch, MagicMock

import gizli_maskele
from gizli_maskele import (
    reset_trace_context,
    start_span,
    end_span,
    get_trace_context,
    get_trace_id,
    get_current_span_id,
    get_traces,
)


def test_trace_context_creation():
    """Test that trace context is created properly."""
    # Reset any existing context
    reset_trace_context()
    
    # Get fresh context
    ctx = get_trace_context()
    
    # Should have trace ID, span ID, start time, and spans list
    assert hasattr(ctx, 'trace_id')
    assert hasattr(ctx, 'span_id')
    assert hasattr(ctx, 'start_time')
    assert hasattr(ctx, 'spans')
    
    # Trace ID should be a UUID string
    assert isinstance(ctx.trace_id, str)
    assert len(ctx.trace_id) > 0
    
    # Initial span ID should be set
    assert isinstance(ctx.span_id, str)
    assert len(ctx.span_id) > 0
    
    # Start time should be a recent timestamp
    assert isinstance(ctx.start_time, float)
    assert ctx.start_time <= time.time()
    
    # Spans list should be initialized
    assert isinstance(ctx.spans, list)


def test_trace_id_uniqueness():
    """Test that trace IDs are unique."""
    reset_trace_context()
    ctx1 = get_trace_context()
    trace_id1 = ctx1.trace_id
    
    reset_trace_context()
    ctx2 = get_trace_context()
    trace_id2 = ctx2.trace_id
    
    assert trace_id1 != trace_id2


def test_span_creation_and_management():
    """Test span creation, nesting, and ending."""
    reset_trace_context()
    
    # Create root span
    root_span_id = start_span("root_operation")
    ctx = get_trace_context()
    
    # Should be the current span
    assert get_current_span_id() == root_span_id
    
    # Should be in spans list
    span_found = False
    for span in ctx.spans:
        if span['span_id'] == root_span_id:
            span_found = True
            assert span['operation_name'] == "root_operation"
            assert span['parent_span_id'] is None or span['parent_span_id'] == ctx.span_id
            assert span['start_time'] is not None
            assert span['end_time'] is None  # Not ended yet
            break
    assert span_found, "Root span not found in spans list"
    
    # Create child span
    child_span_id = start_span("child_operation", root_span_id)
    
    # Should be the current span
    assert get_current_span_id() == child_span_id
    
    # Should have parent set to root span
    ctx = get_trace_context()
    child_span_found = False
    for span in ctx.spans:
        if span['span_id'] == child_span_id:
            child_span_found = True
            assert span['operation_name'] == "child_operation"
            assert span['parent_span_id'] == root_span_id
            assert span['start_time'] is not None
            assert span['end_time'] is None  # Not ended yet
            break
    assert child_span_found, "Child span not found in spans list"
    
    # End child span
    end_span(child_span_id)
    
    # Child span should now have end time
    ctx = get_trace_context()
    for span in ctx.spans:
        if span['span_id'] == child_span_id:
            assert span['end_time'] is not None
            assert span['end_time'] >= span['start_time']
            break
    
    # Current span should be back to root
    assert get_current_span_id() == root_span_id
    
    # End root span
    end_span(root_span_id)
    
    # Root span should now have end time
    ctx = get_trace_context()
    for span in ctx.spans:
        if span['span_id'] == root_span_id:
            assert span['end_time'] is not None
            assert span['end_time'] >= span['start_time']
            break


def test_get_traces_function():
    """Test the get_traces function returns correct structure."""
    reset_trace_context()
    
    # Create a few spans
    root_id = start_span("root")
    child_id = start_span("child", root_id)
    end_span(child_id)
    end_span(root_id)
    
    # Get traces
    traces = get_traces()
    
    # Should return dict with trace_id and spans
    assert isinstance(traces, dict)
    assert 'trace_id' in traces
    assert 'spans' in traces
    
    # Trace ID should match
    assert traces['trace_id'] == get_trace_id()
    
    # Spans should be a list
    assert isinstance(traces['spans'], list)
    assert len(traces['spans']) == 2
    
    # Check span structure
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
        if span['end_time'] is not None:
            assert span['end_time'] >= span['start_time']


def test_json_log_includes_trace_context():
    """Test that json_log includes trace context when available."""
    reset_trace_context()
    
    # Create a span to establish context
    span_id = start_span("test_operation")
    
    # Capture print output (since json_log prints to stdout)
    import io
    import sys
    
    old_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()
    
    try:
        # Call json_log
        gizli_maskele.json_log("Test message", project="test_project", value=42)
        
        # Get the output
        output = captured_output.getvalue().strip()
        
        # Should be valid JSON
        log_entry = json.loads(output)
        
        # Should contain our fields
        assert log_entry["message"] == "Test message"
        assert log_entry["project"] == "test_project"
        assert log_entry["value"] == 42
        assert log_entry["level"] == "INFO"
        assert "timestamp" in log_entry
        
        # Should contain trace context
        assert "trace_id" in log_entry
        assert "span_id" in log_entry
        assert log_entry["trace_id"] == get_trace_id()
        assert log_entry["span_id"] == span_id
        
    finally:
        sys.stdout = old_stdout


def test_json_log_without_trace_context():
    """Test that json_log works without trace context."""
    reset_trace_context()
    
    # Clear trace context
    if hasattr(gizli_maskele._trace_context, 'trace_id'):
        delattr(gizli_maskele._trace_context, 'trace_id')
    if hasattr(gizli_maskele._trace_context, 'span_id'):
        delattr(gizli_maskele._trace_context, 'span_id')
    
    # Capture print output
    import io
    import sys
    
    old_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()
    
    try:
        # Call json_log
        gizli_maskele.json_log("Test message", test_field="test_value")
        
        # Get the output
        output = captured_output.getvalue().strip()
        
        # Should be valid JSON
        log_entry = json.loads(output)
        
        # Should contain our fields
        assert log_entry["message"] == "Test message"
        assert log_entry["test_field"] == "test_value"
        assert log_entry["level"] == "INFO"
        assert "timestamp" in log_entry
        
        # Should NOT contain trace context
        assert "trace_id" not in log_entry
        assert "span_id" not in log_entry
        
    finally:
        sys.stdout = old_stdout


def test_reset_trace_context():
    """Test that reset_trace_context clears the context properly."""
    # Establish context
    reset_trace_context()
    ctx1 = get_trace_context()
    old_trace_id = ctx1.trace_id
    old_span_id = ctx1.span_id
    
    # Reset context
    reset_trace_context()
    
    # Get new context
    ctx2 = get_trace_context()
    
    # Should have different IDs
    assert ctx2.trace_id != old_trace_id
    assert ctx2.span_id != old_span_id
    
    # Spans list should be reset
    assert ctx2.spans == []


def test_nested_spans():
    """Test deeply nested span creation and ending."""
    reset_trace_context()
    
    # Create nested spans: A -> B -> C -> D
    a_id = start_span("A")
    b_id = start_span("B", a_id)
    c_id = start_span("C", b_id)
    d_id = start_span("D", c_id)
    
    # Should be at D
    assert get_current_span_id() == d_id
    
    # End in reverse order: D -> C -> B -> A
    end_span(d_id)
    assert get_current_span_id() == c_id
    
    end_span(c_id)
    assert get_current_span_id() == b_id
    
    end_span(b_id)
    assert get_current_span_id() == a_id
    
    end_span(a_id)
    
    # Verify all spans have end times
    ctx = get_trace_context()
    span_map = {span['span_id']: span for span in ctx.spans}
    
    for span_id in [a_id, b_id, c_id, d_id]:
        assert span_id in span_map
        span = span_map[span_id]
        assert span['end_time'] is not None
        assert span['end_time'] >= span['start_time']


def test_span_timing_accuracy():
    """Test that span timing is reasonably accurate."""
    reset_trace_context()
    
    span_id = start_span("timed_operation")
    
    # Sleep for a known duration
    time.sleep(0.01)  # 10ms
    
    end_span(span_id)
    
    # Check duration
    ctx = get_trace_context()
    for span in ctx.spans:
        if span['span_id'] == span_id:
            duration = span['end_time'] - span['start_time']
            # Should be approximately 0.01 seconds (allowing for system latency)
            assert 0.005 <= duration <= 0.05, f"Duration {duration}s not in expected range"
            break
    else:
        assert False, "Span not found"


if __name__ == "__main__":
    # Run tests if executed directly
    import pytest
    pytest.main([__file__, "-v"])