"""Standalone entry point for the PyInstaller bundle of the Whisper Flow server.

When frozen by PyInstaller, this sets WHISPERFLOW_MODELS_DIR to point at the
bundled model files inside _MEIPASS, then starts uvicorn.
"""

import os
import sys

if getattr(sys, 'frozen', False):
    # Running inside a PyInstaller --onedir bundle.
    # _MEIPASS is the directory that contains the extracted bundle.
    os.environ.setdefault(
        'WHISPERFLOW_MODELS_DIR',
        os.path.join(sys._MEIPASS, 'models'),
    )

# Import the app object directly so PyInstaller can trace all dependencies.
from whisperflow.fast_server import app  # noqa: E402
import uvicorn  # noqa: E402

if __name__ == '__main__':
    port = int(os.environ.get('WHISPERFLOW_PORT', '8181'))
    uvicorn.run(
        app,
        host='127.0.0.1',
        port=port,
        log_level='warning',
    )
