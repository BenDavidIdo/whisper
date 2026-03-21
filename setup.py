"""Setup configuration for whisperflow package."""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="whisperflow",
    version="1.1.0",
    author="Whisper Flow Clone",
    description="Real-time speech-to-text streaming using OpenAI Whisper",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "openai-whisper",
        "torch",
        "numpy",
        "fastapi>=0.108.0",
        "uvicorn[standard]>=0.30.1",
        "websockets>=12.0",
        "python-multipart>=0.0.9",
        "httpx>=0.27.0",
    ],
    extras_require={
        "audio": ["PyAudio>=0.2.14"],
        "dev": [
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
            "pytest-timeout",
            "pytest-benchmark",
            "black",
            "pylint",
            "pylint-fail-under",
            "jiwer",
            "pandas",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
