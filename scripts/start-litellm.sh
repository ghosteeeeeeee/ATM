#!/bin/bash
# Source API keys then start litellm proxy
set -e
source /root/.hermes/.env
export $(grep -v '^#' /root/.hermes/.env | xargs)
exec litellm --model openai/gpt-4o-mini --port 4000 --drop_params --verbose 2>&1
