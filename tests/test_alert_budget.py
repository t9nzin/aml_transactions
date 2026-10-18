import numpy as np
import pytest

from aml.alert_budget import best_cutoff, threshold_curve


def test_curve_counts_alerts_and_catches_from_the_top():
    scores = np.array([0.9, 0.8, 0.7, 0.6, 0.5])
    labels = np.array([1, 0, 1, 0, 1])
    curve = threshold_curve(scores, labels)
    np.testing.assert_array_equal(curve["alerts"], [1, 2, 3, 4, 5])
    np.testing.assert_array_equal(curve["caught"], [1, 1, 2, 2, 3])
    np.testing.assert_allclose(curve["precision"], [1, 0.5, 2 / 3, 0.5, 0.6])
    np.testing.assert_allclose(curve["recall"], [1 / 3, 1 / 3, 2 / 3, 2 / 3, 1])


def test_budget_picks_lowest_threshold_that_fits():
    scores = np.array([0.1, 0.9, 0.7, 0.8, 0.2])
    labels = np.array([0, 1, 1, 0, 1])
    result = best_cutoff(scores, labels, budget=3)
    assert (result.alerts, result.caught, result.threshold) == (3, 2, 0.7)
    assert result.precision == pytest.approx(2 / 3)
    assert result.recall == pytest.approx(2 / 3)


def test_ties_at_the_boundary_never_exceed_the_budget():
    scores = np.array([0.9, 0.5, 0.5, 0.5, 0.1])
    labels = np.array([0, 1, 1, 1, 0])
    result = best_cutoff(scores, labels, budget=3)
    # Flagging 0.5 would mean 4 alerts, so only the top score is flagged.
    assert (result.alerts, result.caught) == (1, 0)


def test_budget_larger_than_population_flags_everything():
    result = best_cutoff(np.array([0.3, 0.2]), np.array([1, 0]), budget=500)
    assert (result.alerts, result.caught, result.recall) == (2, 1, 1.0)


def test_shape_mismatch_raises():
    with pytest.raises(ValueError):
        threshold_curve(np.array([0.1, 0.2]), np.array([1]))
