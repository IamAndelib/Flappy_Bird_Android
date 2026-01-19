# Building Flappy Bird for Android

This project uses **pygame-ce** and **Buildozer** to target Android (arm64-v8a and armeabi-v7a).

## 1. Environment Setup

The build requires a Python 3.11 virtual environment with specific versions of Cython and Setuptools to avoid compatibility issues with the `pygame` recipe.

```bash
# Create and activate venv
python3.11 -m venv .venv
source .venv/bin/activate

# Install specific dependencies
pip install "Cython<3.0" "setuptools<71.0.0" buildozer
```

## 2. Key Patches applied

### Pygame Recipe
The `pygame` recipe in `.buildozer/android/platform/python-for-android/pythonforandroid/recipes/pygame/__init__.py` has been patched to:
1.  **Use pygame-ce**: Version set to `2.5.3` with the `pygame-ce` GitHub URL.
2.  **Sanitize Host Flags**: A regex-based cleaner removes leaked host machine flags (like `-march=x86-64`, `-fcf-protection`) that cause cross-compilation failures.
3.  **Sysconfig Patching**: At runtime, `sysconfig.get_config_vars` is intercepted to strip forbidden flags during the `setup.py` execution.

### Buildozer Configuration
- `android.archs = arm64-v8a, armeabi-v7a`
- `requirements = python3,pygame,android`
- `p4a.branch = master`

## 3. Build & Deploy Commands

Always ensure the virtual environment's `bin` is in your `PATH` so Buildozer can find the correct `cython` and `python` binaries.

### Standard Build (Foreground)
```bash
export PATH="$(pwd)/.venv/bin:$PATH"
buildozer android debug deploy run
```

### Background Build (with logging)
```bash
export PATH="$(pwd)/.venv/bin:$PATH"
buildozer android debug deploy run > mybuild.log 2>&1 &
```

## 4. Troubleshooting
- **Missing Cython**: If Buildozer complains about Cython, double-check that `.venv/bin` is in the `PATH`.
- **Architecture Mismatch**: If the APK fails to install, ensure `android.archs` matches the connected device (usually `arm64-v8a` for modern phones).
- **Logcat**: Use `adb logcat -s python` to see app-specific logs.
