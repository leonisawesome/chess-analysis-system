from setuptools import setup, find_packages

setup(
    name="chess-rag-system",
    version="0.1.0",
    description="Chess RAG Educational Value Scoring System",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "tqdm",
        "PyPDF2",
        "sentence-transformers",
        "scikit-learn",
        "numpy",
        "torch",
        "transformers",
        "safetensors",
        "pyyaml",
        "requests",
        "urllib3",
        "certifi",
    ],
    entry_points={
        'console_scripts': [
            'chess-rag-system=chess_rag_system.cli.main:main',
        ],
    },
)
