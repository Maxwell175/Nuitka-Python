rem Go home.
cd %~dp0

set PGO_OPT=--pgo
set ARCH_OPT=-x64

:CheckOpts
if "%~1" EQU "-x86" (set BUILDX86=-x86) && shift && goto CheckOpts
if "%~1" EQU "-x64" (set ARCH_OPT=-x64) && shift && goto CheckOpts
if "%~1" EQU "--disable-pgo" (set PGO_OPT=) && shift && goto CheckOpts


rem Remove old output
del /S /Q output nuget-result >nul

rem Build with nuget, it solves the directory structure for us.
call .\Tools\nuget\build.bat -x64 %ARCH_OPT% %PGO_OPT%

rem Install with nuget into a build folder
.\externals\windows-installer\nuget\nuget.exe install python -Source %~dp0\PCbuild\amd64 -OutputDirectory nuget-result

rem Move the standalone build result to "output". TODO: Version number could be queried here
rem from the Python binary built, or much rather we do not use one in the nuget build at all.
xcopy /i /q /s /y nuget-result\python.3.9.5\tools output

echo "Ok, Nuitka Python now lives in output folder"

