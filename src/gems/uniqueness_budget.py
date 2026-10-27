"""Dependency-free exact arithmetic shared by frozen and fresh raster checks."""

from fractions import Fraction


def bounds(covered: int, uncovered: int, dots: int, limit: Fraction) -> dict:
    """Necessary bound only; equality at the limit is not a literal failure."""
    if (
        any(type(v) is not int for v in (covered, uncovered, dots))
        or covered < 0
        or uncovered < 0
        or dots <= 0
        or dots > covered + uncovered
    ):
        raise ValueError("Invalid integer footprint or candidate size")
    if not isinstance(limit, Fraction) or not 0 <= limit < 1:
        raise ValueError("Exact rational overlap limit must be in [0, 1)")
    minimum = Fraction(max(0, dots - uncovered), dots)
    maximum = min(covered + uncovered, int(Fraction(uncovered) / (1 - limit)))
    return {
        "candidate_dots": dots,
        "minimum_possible_directed_overlap": float(minimum),
        "overlap_limit": float(limit),
        "necessarily_fails_literal_gate": minimum > limit,
        "maximum_dots_not_ruled_out_by_this_bound": maximum,
        "interpretation": "Necessary condition only; not evidence of novelty or scientific merit",
    }
