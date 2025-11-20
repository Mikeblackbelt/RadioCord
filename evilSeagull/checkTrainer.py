import os

final_model_dir = r"C:\Users\mmati\OneDrive\Documents\GitHub\RadioCord\final-model-gpt2"

if os.path.exists(final_model_dir):
    print("Final model exists with files:", os.listdir(final_model_dir))
else:
    print("Final model directory not found. Did training finish?")

def thisFunctionDoesNothing() -> None:
    return