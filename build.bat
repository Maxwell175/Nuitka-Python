setlocal enableextensions
@echo on

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

set NUGET_PYTHON_PACKAGE_NAME=python
set ARCH_NAME=amd64
if "%ARCH_OPT%" EQU "-x86" (
    set NUGET_PYTHON_PACKAGE_NAME=pythonx86
    set ARCH_NAME=win32
)


rem Remove old output
del /S /Q output nuget-result-%NUGET_PYTHON_PACKAGE_NAME% >nul

move .\Lib\pip.py .\Lib\pip.py.bak

rem Build with nuget, it solves the directory structure for us.
call .\Tools\nuget\build.bat %ARCH_OPT% %PGO_OPT% %REBUILD_OPT%

rem Install with nuget into a build folder
.\externals\windows-installer\nuget\nuget.exe install %NUGET_PYTHON_PACKAGE_NAME% -Source %~dp0\PCbuild\%ARCH_NAME% -OutputDirectory nuget-result-%NUGET_PYTHON_PACKAGE_NAME%

move .\Lib\pip.py.bak .\Lib\pip.py

rem Move the standalone build result to "output". TODO: Version number could be queried here
rem from the Python binary built, or much rather we do not use one in the nuget build at all.

set OUTPUT_DIR=output
set SRC_TOOLS_DIR=nuget-result-%NUGET_PYTHON_PACKAGE_NAME%\%NUGET_PYTHON_PACKAGE_NAME%.3.11.9\tools
set SRC_LIB_DIR=%%d\amd64
if "%ARCH_OPT%" EQU "-x86" (
    set OUTPUT_DIR=output32
    set SRC_LIB_DIR=%%d\win32
)

move %SRC_TOOLS_DIR%\Lib\pip.py.bak %SRC_TOOLS_DIR%\Lib\pip.py
copy %SRC_TOOLS_DIR%\python311.lib %SRC_TOOLS_DIR%\libs\python311.lib

xcopy /i /q /s /y %SRC_TOOLS_DIR% %OUTPUT_DIR%

for /d %%d in (externals\openssl*) do (
   xcopy /i /q /s /y %SRC_LIB_DIR%\*.lib %OUTPUT_DIR%\dependency_libs\openssl\lib && xcopy /i /q /s /y %SRC_LIB_DIR%\include %OUTPUT_DIR%\dependency_libs\openssl\include 
)

for /d %%d in (externals\libffi*) do (
   xcopy /i /q /s /y %SRC_LIB_DIR%\include %OUTPUT_DIR%\dependency_libs\libffi\include
)

%OUTPUT_DIR%\python.exe -m rebuildpython

echo "Ok, Nuitka Python now lives in %OUTPUT_DIR% folder"

endlocal

