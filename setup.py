import setuptools

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name='sweagent',
    author='John Yang',
    author_email='byjohnyang@gmail.com',
    description='The official SWE-agent package - an open source Agent Computer Interface for running language models as software engineers',
    keywords='nlp, agents, code',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://swe-agent.com',
    project_urls={
        'Documentation': 'https://github.com/princeton-nlp/SWE-agent',
        'Bug Reports': 'http://github.com/princeton-nlp/SWE-agent/issues',
        'Source Code': 'http://github.com/princeton-nlp/SWE-agent',
        'Website': 'https://sweagent.com',
    },
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.9',
    install_requires=[
        'anthropic[bedrock]',
        'config',
        'datasets',
        'docker',
        'gymnasium',
        'numpy',
        'openai>=1.0',
        'pandas',
        'rich',
        'ollama',
        'ruamel.yaml',
        'simple-parsing',
        'swebench>=1.0.1',
        'tenacity',
        'together',
        'unidiff',
        'rich-argparse',
    ],
    include_package_data=True,
)
