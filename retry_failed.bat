@echo off
echo ================================================================================
echo Retrying Failed Files
echo ================================================================================
echo.
echo This will retry the 28 files that failed during initial ingestion.
echo.
echo Features:
echo - Longer timeout (120 seconds)
echo - Smaller batches (10 chunks at a time)
echo - Automatic retry (up to 3 attempts per file)
echo - Delay between batches to prevent timeouts
echo.
pause
echo.
echo Starting retry...
echo.
python retry_failed_files.py
echo.
echo.
echo ================================================================================
echo Retry Complete!
echo ================================================================================
echo Check retry_ingestion.log for details
echo.
pause
