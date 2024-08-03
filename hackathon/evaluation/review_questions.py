from datasets import load_dataset

d = load_dataset("princeton-nlp/SWE-bench_Lite")

print(d['dev'][0]['instance_id'])