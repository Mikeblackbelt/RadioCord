from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    DataCollatorForLanguageModeling,
    Trainer
)
from peft import LoraConfig, get_peft_model
import torch
import os

output_dir = r"C:\Users\mmati\OneDrive\Documents\GitHub\RadioCord\ft-output"
final_model_dir = r"C:\Users\mmati\OneDrive\Documents\GitHub\RadioCord\final-model-gpt2"

os.makedirs(output_dir, exist_ok=True)
os.makedirs(final_model_dir, exist_ok=True)


model_name = "gpt2"  # GRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR 

tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
tokenizer.pad_token = tokenizer.eos_token  # UwU Owo im catboy 

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float32  # no float-16s allowed
)

model.gradient_checkpointing_enable()


dataset = load_dataset("json", data_files="promptData.jsonl", split="train")

def preprocess(batch):
    # prompt + response
    text = [f"{p}\n{r}" for p, r in zip(batch["prompt"], batch["response"])]
    enc = tokenizer(text, truncation=True, max_length=256)  
    enc["labels"] = enc["input_ids"].copy()
    return enc

dataset = dataset.map(preprocess, batched=True)


lora_cfg = LoraConfig(
    r=4,  
    lora_alpha=16,
    lora_dropout=0.1,
    target_modules=["c_attn"],  
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_cfg)

args = TrainingArguments(
    output_dir=output_dir,
    per_device_train_batch_size=1,         
    gradient_accumulation_steps=1,         
    num_train_epochs=1,                     
    learning_rate=5e-5,
    fp16=False,                             # my computer lowk shit
    bf16=False,
    logging_steps=10,
    save_steps=50,
    save_total_limit=2,
    gradient_checkpointing=True,            # keep sanity
    optim="adamw_torch"
)

collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False
)

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=dataset,
    data_collator=collator
)

trainer.train()

model.save_pretrained(final_model_dir)
tokenizer.save_pretrained(final_model_dir)

print("Saved:", final_model_dir)
