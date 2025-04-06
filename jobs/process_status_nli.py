
from transformers import pipeline

classifier = pipeline(
    "zero-shot-classification",
    model="tasksource/ModernBERT-base-nli")