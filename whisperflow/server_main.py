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

import uvicorn  # noqa: E402 — import after env var is set

if __name__ == '__main__':
    port = int(os.environ.get('WHISPERFLOW_PORT', '8181'))
    uvicorn.run(
        'whisperflow.fast_server:app',
        host='127.0.0.1',
        port=port,
        log_level='warning',
    )
