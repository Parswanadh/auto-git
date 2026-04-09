@echo off
echo Starting E2E test at %date% %time% > logs\e2e_free_run.txt
D:\.conda\envs\auto-git\python.exe run_e2e_moderate.py >> logs\e2e_free_run.txt 2>&1
echo Finished at %date% %time% >> logs\e2e_free_run.txt
