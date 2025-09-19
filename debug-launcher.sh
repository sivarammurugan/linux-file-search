#!/bin/bash
# Debug launcher to help diagnose taskbar launch issues

echo "$(date): Taskbar launch attempt" >> /tmp/filesearch-debug.log
echo "$(date): Working directory: $(pwd)" >> /tmp/filesearch-debug.log
echo "$(date): Arguments: $@" >> /tmp/filesearch-debug.log

# Try to launch the GUI executable
/home/siva/projects/search/dist/filesearch-gui "$@" 2>&1 | tee -a /tmp/filesearch-debug.log
