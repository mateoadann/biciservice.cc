import multiprocessing

# Worker config
worker_class = "gthread"
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
timeout = 30
preload_app = True

# Reciclado de workers (evita memory leaks)
max_requests = 500
max_requests_jitter = 50

# Logging
accesslog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" %(L)ss'
errorlog = "-"
loglevel = "info"

# Bind
bind = "0.0.0.0:5000"
