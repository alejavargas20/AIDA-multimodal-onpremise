# agents/data/action_classifier/train.py

from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
)
from agents.data.action_classifier.dataset import load_action_dataset
from agents.data.action_classifier.labels import load_labels_from_dataset

MODEL_NAME = "PlanTL-GOB-ES/roberta-base-bne"
DATASET_PATH = "agents/data/catalog/action_training_dataset.json"
OUTDIR = "agents/data/action_classifier/artifacts/roberta_bne_action"

texts, labels_str = load_action_dataset(DATASET_PATH)
labels, label2id, id2label = load_labels_from_dataset(DATASET_PATH)

labels_id = [label2id[l] for l in labels_str]

ds = Dataset.from_dict({"text": texts, "label": labels_id})
ds = ds.train_test_split(test_size=0.2, seed=42)

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)


def tokenize(batch):
    return tokenizer(batch["text"], truncation=True)


ds = ds.map(tokenize, batched=True)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=len(labels),
    id2label=id2label,
    label2id=label2id,
)

args = TrainingArguments(
    output_dir=OUTDIR,
    per_device_train_batch_size=8,
    num_train_epochs=8,
    evaluation_strategy="epoch",
)

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=ds["train"],
    eval_dataset=ds["test"],
    tokenizer=tokenizer,
)

trainer.train()
trainer.save_model(OUTDIR)
tokenizer.save_pretrained(OUTDIR)
