import time

FP = '/root/.hermes/logs/pipeline.log'

def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'{ts} {msg}'
    print(line, flush=True)
    try:
        with open(FP, 'a') as f:
            f.write(line + '\n')
    except:
        pass
