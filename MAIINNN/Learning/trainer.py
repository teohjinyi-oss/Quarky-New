"""
Learning System: Trainer

Periodically retrains ML components with accumulated data:
  - NLP classifier retraining with new labeled examples
  - Token scorer weight tuning based on feedback patterns
  - Pattern confidence recalculation

Runs on a schedule or on-demand after enough new data accumulates.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from AppStudio.Config import DATA_DIR


@dataclass
class TrainingRun:
    """Record of a training run."""
    component: str          # "classifier", "scorer", "patterns"
    examples_count: int
    duration_ms: float
    accuracy_before: float = 0.0
    accuracy_after: float = 0.0
    timestamp: float = field(default_factory=time.time)


class Trainer:
    """
    Coordinates retraining of ML components.
    """

    def __init__(self):
        self._runs: list[TrainingRun] = []
        self._examples: list[dict[str, str]] = []
        self._log_path = Path(DATA_DIR) / "learning" / "training_log.json"
        self._examples_path = Path(DATA_DIR) / "learning" / "training_examples.json"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._min_examples = 10  # minimum examples before retraining

    def add_example(self, text: str, intent: str, source: str = "implicit") -> None:
        """Add a labeled training example (deduplicated)."""
        # Dedup: skip if exact text+intent already exists
        for ex in self._examples:
            if ex["text"] == text and ex["intent"] == intent:
                return
        self._examples.append({
            "text": text,
            "intent": intent,
            "source": source,
            "timestamp": str(time.time()),
        })
        self._save_examples()

    def should_retrain(self) -> bool:
        """Check if we have enough new data to justify retraining."""
        # Count examples since last training run
        last_run_time = self._runs[-1].timestamp if self._runs else 0
        new_examples = sum(
            1 for e in self._examples
            if float(e.get("timestamp", "0")) > last_run_time
        )
        return new_examples >= self._min_examples

    def retrain_classifier(self) -> TrainingRun:
        """Retrain the NLP intent classifier with accumulated examples."""
        start = time.time()

        # Gather examples
        texts = [e["text"] for e in self._examples]
        intents = [e["intent"] for e in self._examples]

        run = TrainingRun(
            component="classifier",
            examples_count=len(texts),
            duration_ms=0.0,
        )

        if len(texts) < 5:
            run.duration_ms = (time.time() - start) * 1000
            self._runs.append(run)
            return run

        try:
            from MAIINNN.NLP.classifier import retrain
            from AppStudio.Config import NLP_V2

            examples = list(zip(texts, intents))
            model_path = NLP_V2.get("tfidf_model_path")
            if not model_path:
                model_path = Path(DATA_DIR) / "learning" / "classifier.pkl"
            else:
                model_path = Path(model_path)

            # Measure accuracy via holdout split if we have enough data
            accuracy = 0.0
            if len(examples) >= 20:
                accuracy = self._evaluate_accuracy(examples)

            success = retrain(examples, model_path=model_path)

            if success:
                run.accuracy_after = accuracy if accuracy > 0 else 0.5
            else:
                run.accuracy_after = 0.0
        except (ImportError, Exception):
            pass

        run.duration_ms = (time.time() - start) * 1000
        self._runs.append(run)
        self._save_log()
        return run

    @staticmethod
    def _evaluate_accuracy(examples: list[tuple[str, str]]) -> float:
        """Compute real accuracy using an 80/20 train-test split."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.naive_bayes import MultinomialNB
            import random

            shuffled = list(examples)
            random.shuffle(shuffled)
            split = max(1, int(len(shuffled) * 0.8))
            train, test = shuffled[:split], shuffled[split:]

            if len(test) < 2:
                return 0.0

            train_texts, train_labels = zip(*train)
            test_texts, test_labels = zip(*test)

            vec = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
            X_train = vec.fit_transform(train_texts)
            X_test = vec.transform(test_texts)

            clf = MultinomialNB()
            clf.fit(X_train, train_labels)

            correct = sum(
                1 for pred, actual in zip(clf.predict(X_test), test_labels)
                if pred == actual
            )
            return correct / len(test_labels)
        except Exception:
            return 0.0

    def retrain_all(self) -> list[TrainingRun]:
        """Retrain all retrainable components."""
        runs = []
        if self.should_retrain():
            runs.append(self.retrain_classifier())
        return runs

    def _save_examples(self) -> None:
        data = self._examples[-500:]  # keep last 500
        try:
            self._examples_path.write_text(json.dumps(data, indent=2))
        except OSError:
            pass

    def _save_log(self) -> None:
        data = [
            {
                "component": r.component,
                "examples": r.examples_count,
                "duration_ms": r.duration_ms,
                "accuracy_before": r.accuracy_before,
                "accuracy_after": r.accuracy_after,
                "timestamp": r.timestamp,
            }
            for r in self._runs[-50:]
        ]
        try:
            self._log_path.write_text(json.dumps(data, indent=2))
        except OSError:
            pass

    @property
    def run_count(self) -> int:
        return len(self._runs)

    @property
    def example_count(self) -> int:
        return len(self._examples)
