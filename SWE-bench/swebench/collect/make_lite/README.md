## SWE-bench *Lite*
This directory contains the scripts used to make the *lite* version of SWE-bench. The *lite* version is a subset of the full SWE-bench, that filters out certain types of instances to make evaluation on SWE-bench a bit cheaper and more accessible.

SWE-bench lite consists of 300 test instances and 23 development instances; both subsets of the full SWE-bench splits. We filter the full SWE-bench according to the following criteria to get *lite*:
- We remove instances with images, external hyperlinks, references to specific commit shas and references to other pull requests or issues.
- We remove instances that have fewer than 40 words in the problem statement.
- We remove instances that edit more than 1 file.
- We remove instances where the gold patch has more than 3 edit hunks (see [patch](https://man7.org/linux/man-pages/man1/patch.1.html)).
- We remove instances that create or remove files.
- We remove instances that contain tests with error message checks.
- Finally, we sample 300 test instances and 23 development instances from the remaining instances.

See `make_lite.py` for the script that makes the *lite* version of SWE-bench, or download the *lite* version from the Hugging Face datasets [princeton-nlp/SWE-bench_Lite](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite)
