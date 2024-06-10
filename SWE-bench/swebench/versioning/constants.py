# Constants - Task Instance Version File
MAP_REPO_TO_VERSION_PATHS = {
    "dbt-labs/dbt-core": ["core/dbt/version.py", "core/dbt/__init__.py"],
    "django/django": ["django/__init__.py"],
    "huggingface/transformers": ["src/transformers/__init__.py"],
    "marshmallow-code/marshmallow": ["src/marshmallow/__init__.py"],
    "mwaskom/seaborn": ["seaborn/__init__.py"],
    "pallets/flask": ["src/flask/__init__.py", "flask/__init__.py"],
    "psf/requests": ["requests/__version__.py", "requests/__init__.py"],
    "pyca/cryptography": [
        "src/cryptography/__about__.py",
        "src/cryptography/__init__.py",
    ],
    "pylint-dev/astroid": ["astroid/__pkginfo__.py", "astroid/__init__.py"],
    "pylint-dev/pylint": ["pylint/__pkginfo__.py", "pylint/__init__.py"],
    "pytest-dev/pytest": ["src/_pytest/_version.py", "_pytest/_version.py"],
    "pyvista/pyvista": ["pyvista/_version.py", "pyvista/__init__.py"],
    "Qiskit/qiskit": ["qiskit/VERSION.txt"],
    "scikit-learn/scikit-learn": ["sklearn/__init__.py"],
    "sphinx-doc/sphinx": ["sphinx/__init__.py"],
    "sympy/sympy": ["sympy/release.py", "sympy/__init__.py"],
}

# Cosntants - Task Instance Version Regex Pattern
MAP_REPO_TO_VERSION_PATTERNS = {
    k: [r'__version__ = [\'"](.*)[\'"]', r"VERSION = \((.*)\)"]
    for k in [
        "dbt-labs/dbt-core",
        "django/django",
        "huggingface/transformers",
        "marshmallow-code/marshmallow",
        "mwaskom/seaborn",
        "pallets/flask",
        "psf/requests",
        "pyca/cryptography",
        "pylint-dev/astroid",
        "pylint-dev/pylint",
        "scikit-learn/scikit-learn",
        "sphinx-doc/sphinx",
        "sympy/sympy",
    ]
}
MAP_REPO_TO_VERSION_PATTERNS.update(
    {
        k: [
            r'__version__ = [\'"](.*)[\'"]',
            r'__version__ = version = [\'"](.*)[\'"]',
            r"VERSION = \((.*)\)",
        ]
        for k in ["pytest-dev/pytest", "matplotlib/matplotlib"]
    }
)
MAP_REPO_TO_VERSION_PATTERNS.update({k: [r"(.*)"] for k in ["Qiskit/qiskit"]})
MAP_REPO_TO_VERSION_PATTERNS.update({k: [r"version_info = [\d]+,[\d\s]+,"] for k in ["pyvista/pyvista"]})

SWE_BENCH_URL_RAW = "https://raw.githubusercontent.com/"