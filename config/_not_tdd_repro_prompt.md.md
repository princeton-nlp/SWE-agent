## Reproduction Requirements

1. Always start by replicating the bug that is discussed in the ISSUE.
     * We recommend that you always first reproduce a test or script that reproduces the bug in your environment. Execute and verify that you can repro it.
2. Once repro'ed start fixing it.
  * When you think you've fixed the bug, re-run the bug reproduction script to make sure that the bug has indeed been fixed.
  * If the bug reproduction script does not print anything when it successfully runs, we recommend adding a print("Script completed successfully, no errors.") command at the end of the file, so that you can be sure that the script indeed ran fine all the way through.
3. If the bug reproduction script requires inputting/reading a specific file, such as buggy-input.png, and you'd like to understand how to input that file, conduct a search in the existing repo code, to see whether someone else has already done that. Do this by running the command: find_file "buggy-input.png" If that doesn't work, use `search_file` or `find` etc.
