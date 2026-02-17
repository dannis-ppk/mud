@echo off
echo ========================================================
echo   Save Changes (Upload to GitHub)
echo ========================================================
echo.
set /p msg="Enter a note for this change (e.g., Fixed bug): "
if "%msg%"=="" set msg="Update from Batch Script"

echo.
echo 1. Adding files...
git add .
echo.
echo 2. Saving (Commit)...
git commit -m "%msg%"
echo.
echo 3. Uploading (Push)...
git push
echo.
echo Done! Your changes are safe on GitHub.
pause
