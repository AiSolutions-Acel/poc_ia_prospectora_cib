# Metrics utilities (currently handled within use cases, but can be extracted here if needed)
def calculate_latency(t_start: float, t_end: float) -> float:
    """Calculates latency in milliseconds."""
    return (t_end - t_start) * 1000
