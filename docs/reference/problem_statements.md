# Specifying problems

We currently support the following input types:

* A string of text (`TextProblemStatement`)
* A path to a file on the local filesystem (`FileProblemStatement`)
* A URL to a GitHub issue (`GithubIssue`)
* An empty problem statement (`EmptyProblemStatement`)

With `sweagent run`, you can specify the problem statement type with the `--problem-statement` flag.
For example:

```bash title="From text"
--problem-statement.text="This is a problem statement"
--problem-statement.type=text
```

```bash title="From a file"
--problem-statement.path=path/to/file.txt
--problem-statement.type=text_file
```

```bash title="From a GitHub issue"
--problem-statement.url=https://github.com/org/repo/issues/123
--problem-statement.type=github_issue
```

See below for more details on the configuration options.


All of these classes are defined in `sweagent.environment.config.problem_statement`.

::: sweagent.environment.config.problem_statement.problem_statement_from_simplified_input
    options:
        show_root_full_path: false
        show_bases: false

::: sweagent.environment.config.problem_statement.TextProblemStatement
    options:
        show_root_full_path: false
        show_bases: false


::: sweagent.environment.config.problem_statement.FileProblemStatement
    options:
        show_root_full_path: false
        show_bases: false

::: sweagent.environment.config.problem_statement.GithubIssue
    options:
        show_root_full_path: false
        show_bases: false

::: sweagent.environment.config.problem_statement.EmptyProblemStatement
    options:
        show_root_full_path: false
        show_bases: false
