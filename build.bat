setlocal enableextensions

rem Go home.
cd %~dp0

set PGO_OPT=
set ARCH_OPT=-x64
set REBUILD_OPT=

:CheckOpts
if "%~1" EQU "-x86" (set ARCH_OPT=-x86) && shift && goto CheckOpts
if "%~1" EQU "-x64" (set ARCH_OPT=-x64) && shift && goto CheckOpts
if "%~1" EQU "--pgo" (set PGO_OPT=--pgo) && shift && goto CheckOpts
if "%~1" EQU "-r" (set REBUILD_OPT=-r) && shift && goto CheckOpts


rem Remove old output
del /S /Q output nuget-result >nul

rem Build with nuget, it solves the directory structure for us.
call .\Tools\nuget\build.bat %ARCH_OPT% %PGO_OPT% %REBUILD_OPT%

rem Install with nuget into a build folder
.\externals\windows-installer\nuget\nuget.exe install python -Source %~dp0\PCbuild\amd64 -OutputDirectory nuget-result

rem Move the standalone build result to "output". TODO: Version number could be queried here
rem from the Python binary built, or much rather we do not use one in the nuget build at all.
xcopy /i /q /s /y nuget-result\python.3.9.5\tools output

md output\dependency_libs\openssl\lib

for /d %%d in (externals\openssl*) do (
if "%ARCH_OPT%" EQU "-x64" ( xcopy /i /q /s /y %%d\amd64\*.lib output\dependency_libs\openssl\lib && xcopy /i /q /s /y %%d\amd64\include output\dependency_libs\openssl\include ) else ( xcopy /i /q /s /y %%d\win32\*.lib output\dependency_libs\openssl\lib && xcopy /i /q /s /y %%d\win32\include output\dependency_libs\openssl\include )
)

echo "Ok, Nuitka Python now lives in output folder"

endlocal