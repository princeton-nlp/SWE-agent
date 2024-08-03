from datasets import load_dataset

d = load_dataset("princeton-nlp/SWE-bench_Lite")

print(d["dev"][0].keys())
print(d["dev"][0]['hints_text'])
print(d["dev"][0]['patch'])
print(d["dev"][0]['test_patch'])
