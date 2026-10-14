#!/usr/bin/env python3
"""
ml_classifier — Local ML trade quality predictor.

RandomForest classifier trained on historical trades from PostgreSQL.
Predicts win/loss probability before execution. Complements Hebbian
(lookup) with generalization (learns patterns across tokens/signals).

Spec: brain/plans/ml-trade-classifier-spec.md
"""
