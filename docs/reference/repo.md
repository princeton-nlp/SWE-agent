# Configuring repositories

We currently support the following repository types:

* A pre-existing repository (`PreExistingRepo`)
* A local repository (`LocalRepoConfig`)
* A GitHub repository (`GithubRepoConfig`)

With `sweagent run`, you can specify the repository type with the `--env.repo` flag.
For example:

```bash title="From a pre-existing repository"
--env.repo.repo_name="testbed" # (1)!
--env.repo.type=preexisting
```

1. Folder name at the root of the deployment

```bash title="From a local repository"
--env.repo.path=/path/to/repo
--env.repo.type=local
```

All of these classes are defined in `sweagent.environment.config.repo`.

::: sweagent.environment.config.repo.PreExistingRepo
    options:
        show_root_full_path: false
        show_bases: false

::: sweagent.environment.config.repo.LocalRepoConfig
    options:
        show_root_full_path: false
        show_bases: false

::: sweagent.environment.config.repo.GithubRepoConfig
    options:
        show_root_full_path: false
        show_bases: false

::: sweagent.environment.config.repo.repo_from_simplified_input
    options:
        show_root_full_path: false
        show_bases: false
