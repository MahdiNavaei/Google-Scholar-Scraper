# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project_root = Path(SPECPATH).parents[1]
src_path = project_root / "src"
entrypoint = src_path / "google_scholar_scraper" / "__main__.py"
excluded_optional_modules = [
    "aiohttp",
    "cryptography",
    "cv2",
    "Cython",
    "fastapi",
    "flask",
    "lxml",
    "matplotlib",
    "mlflow",
    "nltk",
    "numpy",
    "onnxruntime",
    "openai",
    "pandas",
    "PIL",
    "psutil",
    "pyarrow",
    "PyQt6",
    "pytest",
    "scipy",
    "sklearn",
    "sqlalchemy",
    "torch",
    "torchvision",
    "transformers",
    "uvicorn",
    "win32com",
]


a = Analysis(
    [str(entrypoint)],
    pathex=[str(src_path)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tests", *excluded_optional_modules],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GoogleScholarScraper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Google-Scholar-Scraper-v2.0.0",
)
