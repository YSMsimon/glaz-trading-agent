#!/bin/bash
# Glaz momentum bot — one cycle. Self-gates on market hours + HALT file.
cd /Users/simon/Desktop/alpaca-agent || exit 1
/Users/simon/Desktop/alpaca-agent/.venv/bin/python -m agent.trader >> /Users/simon/Desktop/alpaca-agent/data/bot.log 2>&1
