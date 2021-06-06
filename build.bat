rem Go home.
cd %~dp0

rem Remove old output
del /S /Q output nuget-result >nul

rem Build with nuget, it solves the directory structure for us.
call .\Tools\nuget\build.bat -x64

rem Install with nuget into a build folder
.\externals\windows-installer\nuget\nuget.exe install python -Source %~dp0\PCbuild\amd64 -OutputDirectory nuget-result

rem Move the standalone build result to "output". TODO: Version number could be queried here
rem from the Python binary built, or much rather we do not use one in the nuget build at all.
xcopy nuget-result\python.3.9.5\tools output

echo "Ok, Nuitka Python now lives in output folder"

