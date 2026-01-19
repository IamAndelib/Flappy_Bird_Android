
import sysconfig
import sys
import os

# Original get_config_vars
_orig_get_config_vars = sysconfig.get_config_vars

def patched_get_config_vars(*args, **kwargs):
    res = _orig_get_config_vars(*args, **kwargs)
    
    bad_flags = [
        "-march=x86-64", "-mtune=generic", "-fcf-protection", 
        "-fstack-clash-protection", "-ffat-lto-objects"
    ]
    
    if isinstance(res, dict):
        for key in ["CFLAGS", "CPPFLAGS", "LDFLAGS", "BASECFLAGS", "OPT", "CONFIGURE_CFLAGS"]:
            if key in res and isinstance(res[key], str):
                for flag in bad_flags:
                    res[key] = res[key].replace(flag, "")
                res[key] = " ".join(res[key].split())
    return res

sysconfig.get_config_vars = patched_get_config_vars

# Also patch the environment just in case
bad_flags = ["-march=x86-64", "-mtune=generic", "-fcf-protection", "-fstack-clash-protection", "-ffat-lto-objects"]
for key in ["CFLAGS", "CPPFLAGS", "LDFLAGS"]:
    if key in os.environ:
        for flag in bad_flags:
            os.environ[key] = os.environ[key].replace(flag, "")
        os.environ[key] = " ".join(os.environ[key].split())

# Execute the actual setup.py
# Use ONLY the arguments intended for setup.py
sys.argv = ['setup.py', 'build_ext', '-v']
print(f"DEBUG: patch_sysconfig executing setup.py with argv: {sys.argv}")
with open('setup.py', 'rb') as f:
    code = compile(f.read(), 'setup.py', 'exec')
    exec(code, {'__name__': '__main__', '__file__': 'setup.py'})
