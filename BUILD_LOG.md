# Flappy Bird Android Build Documentation

This document details the process of building and packaging the Flappy Bird Android application using **Pygame-CE**, **Buildozer**, and **Python-for-Android (p4a)**. It specifically addresses the common pitfalls of cross-compiling Python C-extensions for Android.

## 1. Project Overview
- **Game Engine**: Pygame-CE (2.5.3)
- **Packaging Tool**: Buildozer (1.5.0)
- **Target Architectures**: `arm64-v8a`, `armeabi-v7a`
- **Minimum Android API**: 21 (Android 5.0)
- **Target Android API**: 31 (Android 12)
- **NDK Version**: r25b

## 2. Prerequisites & Environment
The build was performed on a Linux (Arch) system with the following setup:
- **Python**: 3.11 (Virtual environment recommended)
- **Java**: OpenJDK 17
- **Dependencies**: `python3, pygame, android` (specified in `buildozer.spec`)
- **Key Python Packages**:
  - `Cython < 3.0` (Pinned to `0.29.37` for compatibility with older recipes)
  - `setuptools == 75.9.1`

## 3. The Core Challenge: Host Flag Leakage
When cross-compiling `pygame` for Android (ARM), the build process often "leaks" compilation flags from the host machine's Python configuration (e.g., `-march=x86-64`, `-fcf-protection`). 

If these flags reach the ARM compiler, the build fails with:
`error: invalid variant 'x86-64'` or similar architecture mismatch errors.

## 4. The Solution: Recipe Patching
To solve the flag leakage, we modified the `pygame` recipe inside the `.buildozer` directory.

### Location of the Recipe:
`.buildozer/android/platform/python-for-android/pythonforandroid/recipes/pygame/__init__.py`

### Key Modifications:
1. **Dynamic Flag Sanitization**: In `get_recipe_env`, we used regex to aggressively strip host flags from `CFLAGS`, `LDFLAGS`, and `CPPFLAGS`.
2. **Monkey-patching `sysconfig`**: Since `setuptools` often fetches flags directly from `sysconfig.get_config_vars()`, we created a wrapper script `patch_sysconfig.py` that is executed during the build.

#### `patch_sysconfig.py` Logic:
This script intercepts calls to `sysconfig.get_config_vars()` and removes problematic flags at runtime before executing `setup.py`:
```python
import sysconfig
# ...
_orig_get_config_vars = sysconfig.get_config_vars

def patched_get_config_vars(*args, **kwargs):
    res = _orig_get_config_vars(*args, **kwargs)
    bad_flags = ["-march=x86-64", "-mtune=generic", "-fcf-protection", ...]
    if isinstance(res, dict):
        for key in ["CFLAGS", "LDFLAGS", ...]:
            for flag in bad_flags:
                res[key] = res[key].replace(flag, "")
    return res

sysconfig.get_config_vars = patched_get_config_vars
```

## 5. Build Instructions
To build the project from scratch with these fixes:

1. **Initialize Buildozer**:
   ```bash
   buildozer init
   ```
2. **Configure `buildozer.spec`**:
   - Ensure `requirements = python3,pygame,android`
   - Set `android.archs = arm64-v8a, armeabi-v7a`
   - Set `p4a.extra_args = ` (Leave empty, do NOT pass `--hostpython` here).
3. **Patch the Recipe**: Apply the `sysconfig` patch to the `pygame` recipe (as detailed in Section 4).
4. **Run the Build**:
   ```bash
   buildozer android debug
   ```

## 6. Troubleshooting "Nitty-Gritties"
- **Unrecognized Argument `--hostpython`**: This error occurs if `--hostpython` is passed to the `p4a apk` command. In newer versions of Buildozer, this flag is only supported during the distribution phase, not the packaging phase. Ensure it is removed from `p4a.extra_args` if packaging fails.
- **Cython 3.0 Errors**: Many older p4a recipes are incompatible with Cython 3.0+. Force `Cython<3.0` in your build environment.
- **Wiping Builds**: If the build gets stuck or cached with bad flags, run:
  ```bash
  buildozer android clean
  # Or more aggressively:
  rm -rf .buildozer/android/platform/build-arm64-v8a_armeabi-v7a/build/other_builds/pygame
  ```

## 7. Artifacts
The final APK is located at:
`bin/flappybird-1.0-arm64-v8a_armeabi-v7a-debug.apk`
