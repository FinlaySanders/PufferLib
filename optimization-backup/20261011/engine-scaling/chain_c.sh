#!/bin/bash
cd /puffertank/experiments/nethack-24h-20261009 && python3 campaign_ablate.py ablate_incstack.json; echo FULL2_DONE
cd /puffertank/experiments/nethack-compact-state-20261008 && nice -n 10 python3 check.py incstack; echo FULLGATE_DONE
cd /puffertank/experiments/nethack-24h-20261009 && nice -n 19 python3 regime_report.py; echo REPORT_DONE
