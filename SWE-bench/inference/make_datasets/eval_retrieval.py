
#!/usr/bin/env python

"""This script can be used to evaluate the BM25 retrieval results for a dataset created with create_text_dataset.py with the --retrieval_file option and --file_source bm25."""

import re
import numpy as np
from datasets import load_dataset, disable_caching, load_from_disk
from argparse import ArgumentParser
import logging

disable_caching()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main(dataset_name_or_path, split):
    try:
        dataset = load_dataset(dataset_name_or_path, split=split)
    except:
        dataset = load_from_disk(dataset_name_or_path, split=split)
    print(f'Evaluating {len(dataset)} instances from {dataset_name_or_path} {split} split')
    instance_files_pattern = re.compile(r'\[start of ([\w\.\-\/]+)\]\n(?:.+?)\n\[end of \1\]', re.DOTALL)
    patch_files_pattern = re.compile(r'\-\-\- a/(.+)')
    patch_files = {instance['instance_id']: instance['patch'] for instance in dataset}
    recalls_any = list()
    recalls_all = list()
    recalls = list()
    for datum in dataset:
        instance_id = datum['instance_id']
        retrieved_files = instance_files_pattern.findall(datum['text'])
        if retrieved_files and 'readme' in retrieved_files[0].lower():
            retrieved_files = retrieved_files[1:]  # first file is usually the readme, we don't want to count that
        retrieved_files = set(retrieved_files)
        gold_files = set(patch_files_pattern.findall(patch_files[instance_id]))
        if len(gold_files) == 0:
            print(f"WARNING: Instance {datum['instance_id']} has no gold files")
            continue
        if len(retrieved_files) == 0:
            print(f"WARNING: Instance {datum['instance_id']} has no retrieved files")
            continue
        recall = len(retrieved_files.intersection(gold_files)) / len(gold_files)
        recalls.append(recall)
        recalls_any.append(int(recall > 0))
        recalls_all.append(int(recall == 1))
    recalls = np.array(recalls)
    recalls_any = np.array(recalls_any)
    recalls_all = np.array(recalls_all)
    print(f"Avg Recall: {np.mean(recalls)*100:.2f}")
    print(f"All Recall: {np.mean(recalls_all)*100:.2f}")
    print(f"Any Recall: {np.mean(recalls_any)*100:.2f}")
    

if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--dataset_name_or_path', type=str, default='princeton-nlp/SWE-bench_bm25_13K')
    parser.add_argument('--split', type=str, default='test')
    args = parser.parse_args()
    main(**vars(args))
