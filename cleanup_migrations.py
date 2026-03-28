import os, sys

base = os.path.join(os.path.dirname(__file__), 'shop', 'migrations')
for f in os.listdir(base):
    if f.startswith('0') and f.endswith('.py'):
        path = os.path.join(base, f)
        os.remove(path)
        print(f'Removed: {f}')
print('Done')
