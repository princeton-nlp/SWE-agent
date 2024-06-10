from criteria import (
    contains_git_commit_hash,
    contains_hyperlinks,
    contains_image,
    contains_issue_reference,
    contains_non_modified_files,
    contains_pytest_match_arg,
    leq_n_code_lines,
    leq_n_files,
    leq_n_hunks,
    leq_n_words,
)
from datasets import load_dataset, disable_caching, DatasetDict
disable_caching()


def filter_problem_statement(instance):
    problem_statement = instance["problem_statement"]
    repo = instance["repo"]
    if leq_n_words(problem_statement, 40) or \
        contains_hyperlinks(problem_statement, repo) or \
        contains_issue_reference(problem_statement, repo) or \
        contains_git_commit_hash(problem_statement) or \
        contains_image(problem_statement):
        return False
    return True


def filter_patch(instance):
    patch_text = instance["patch"]
    if contains_non_modified_files(patch_text) or \
        not leq_n_files(patch_text, 1) or \
        not leq_n_hunks(patch_text, 3):
        return False
    return True


def filter_patch_test(instance):
    patch_text = instance["test_patch"]
    if contains_pytest_match_arg(patch_text):
        return False
    return True


def apply_filters(dset, filters, name=''):
    print(f'Starting with {len(dset)} instances', end='')
    if name:
        print(f' for {name}.')
    else:
        print('.')
    for _filter in filters:
        dset = dset.filter(_filter, desc=f'Applying {_filter.__name__}')
        print(f'After filtering {len(dset)}.')
    return dset


def take_subset(dset, n, name=''):
    dset = dset.sort("instance_id")
    print(f'Starting with {len(dset)} instances', end='')
    if name:
        print(f' for {name}.')
    else:
        print('.')
    dset = dset.shuffle(seed=42).select(range(n))
    print(f'Sampled {len(dset)} instances.')
    return dset


if __name__ == "__main__":
    # Load the dataset
    dev = load_dataset("princeton-nlp/SWE-bench")['dev']
    test = load_dataset("princeton-nlp/SWE-bench")['test']

    test = apply_filters(test, [filter_problem_statement, filter_patch, filter_patch_test], 'test')
    test = take_subset(test, 300, 'test')
    dev = apply_filters(dev, [filter_problem_statement, filter_patch, filter_patch_test], 'dev')
    dset = DatasetDict({'dev': dev, 'test': test})
    # Save the filtered dataset to disk
    dset.save_to_disk("SWE-bench_lite")
    print("Saved to SWE-bench_lite.")