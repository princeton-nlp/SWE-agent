import setuptools

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name='swebench',
    author='John Yang',
    author_email='byjohnyang@gmail.com',
    description='The official SWE-bench package - a benchmark for evaluating LMs on software engineering',
    keywords='nlp, benchmark, code',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://swebench.com',
    project_urls={
        'Documentation': 'https://github.com/princeton-nlp/SWE-bench',
        'Bug Reports': 'http://github.com/princeton-nlp/SWE-bench/issues',
        'Source Code': 'http://github.com/princeton-nlp/SWE-bench',
        'Website': 'https://swebench.com',
    },
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
    install_requires=[
        'beautifulsoup4',
        'chardet',
        'datasets',
        'ghapi',
        'GitPython',
        'python-dotenv',
        'requests',
        'rich',
        'tqdm',
    ],
    include_package_data=True,
)