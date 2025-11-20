from peft import PeftModel
from transformers import AutoTokenizer, AutoModelForCausalLM

model_dir = r"C:\Users\mmati\OneDrive\Documents\GitHub\RadioCord\final-model-gpt2"  # contains adapter files
base = "gpt2"

tokenizer = AutoTokenizer.from_pretrained(base)
model = AutoModelForCausalLM.from_pretrained(base)

model = PeftModel.from_pretrained(model, model_dir)

prompt = "mee6:"
inputs = tokenizer(prompt, return_tensors="pt")

out = model.generate(**inputs, max_length=100)
print(tokenizer.decode(out[0], skip_special_tokens=True))
