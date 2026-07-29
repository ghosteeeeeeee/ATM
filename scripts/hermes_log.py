import time

FP = '/root/.hermes/logs/pipeline.log'

def log(msg, level=None):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'{ts} {msg}' if level is None else f'{ts} [{level}] {msg}'
    print(line, flush=True)
    try:
        with open(FP, 'a') as f:
            f.write(line + '\n')
    except:
        pass
