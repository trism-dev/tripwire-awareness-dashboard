#!/bin/sh
# One image, two services: Railway (or any host) sets SERVICE=app or SERVICE=worker.
# `exec` makes the program PID 1, so it receives stop signals and shuts down cleanly.
case "$SERVICE" in
  app)
    exec streamlit run app/Home.py \
      --server.port "${PORT:-8501}" --server.address 0.0.0.0 \
      --server.headless true --browser.gatherUsageStats false
    ;;
  worker)
    exec python -m worker.run
    ;;
  *)
    echo "Set the SERVICE environment variable to app or worker (got: ${SERVICE:-nothing})." >&2
    exit 1
    ;;
esac
