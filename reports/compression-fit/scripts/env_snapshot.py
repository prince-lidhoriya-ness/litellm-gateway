"""env_snapshot.py -> raw/env.json : machine, OS, Python/package versions, Ollama version + model digest. Run with the same interpreter and PYTHONPATH as compress_all.py."""
import json, os, platform, subprocess, sys, urllib.request, time
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
def sh(cmd):
    try: return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception as e: return f'error: {e}'
def ver(m):
    try: return __import__(m).__version__
    except Exception as e: return f'n/a ({type(e).__name__})'
info = dict(timestamp=time.strftime('%Y-%m-%dT%H:%M:%S%z'), os=platform.platform(), python=sys.version, python_exe=sys.executable,
            cpu=sh('powershell -NoProfile -Command "(Get-CimInstance Win32_Processor).Name"'),
            cores_logical=os.cpu_count(), cores_physical=sh('powershell -NoProfile -Command "(Get-CimInstance Win32_Processor).NumberOfCores"'),
            ram_bytes=sh('powershell -NoProfile -Command "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"'),
            gpu=sh('powershell -NoProfile -Command "(Get-CimInstance Win32_VideoController).Name"'),
            cuda_available=None,
            packages={m: ver(m) for m in ['torch', 'transformers', 'tokenizers', 'huggingface_hub', 'llmlingua', 'numpy', 'scipy', 'sklearn', 'tiktoken', 'psutil']},
            pythonpath=os.environ.get('PYTHONPATH'))
try:
    import torch; info['cuda_available'] = torch.cuda.is_available(); info['torch_threads'] = torch.get_num_threads()
except Exception: pass
try:
    tags = json.loads(urllib.request.urlopen('http://localhost:11434/api/tags', timeout=10).read())
    info['ollama_version'] = json.loads(urllib.request.urlopen('http://localhost:11434/api/version', timeout=10).read())['version']
    info['ollama_models'] = [dict(name=m['name'], digest=m['digest'], size=m['size'], quant=m['details']['quantization_level'], params=m['details']['parameter_size']) for m in tags['models']]
except Exception as e: info['ollama_error'] = str(e)
info['gateway_git_head'] = sh('git -C C:/Users/P7120489/litellm-gateway rev-parse HEAD')
json.dump(info, open(os.path.join(ROOT, 'raw', 'env.json'), 'w'), indent=1)
print(json.dumps(info, indent=1))
