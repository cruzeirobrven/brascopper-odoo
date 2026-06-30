@echo off
title Importar Certificado Brascopper - NF-e
cd /d "%~dp0"

echo =============================================
echo  Importar Certificado A1 Brascopper
echo  Valido ate: 11/03/2027
echo  CNPJ: 22655662000132
echo =============================================
echo.

REM --- Verificar Admin ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] Execute como ADMINISTRADOR!
    echo Clique com direito no arquivo ^> Executar como administrador
    echo.
    pause
    exit /b 1
)

set PFX=C:\BRVEN\CERTIFICADO\E_CNPJ_BRASCOPPER.PFX
set SENHA=@bcd1234E

if not exist "%PFX%" (
    echo [ERRO] Arquivo nao encontrado: %PFX%
    pause
    exit /b 1
)

echo [1/2] Importando certificado no Windows Certificate Store...
powershell -Command "Import-PfxCertificate -FilePath '%PFX%' -CertStoreLocation Cert:\LocalMachine\My -Password (ConvertTo-SecureString '%SENHA%' -AsPlainText -Force)" 2>&1

if %errorlevel% neq 0 (
    echo [ERRO] Falha ao importar certificado!
    pause
    exit /b 1
)
echo [OK] Certificado importado!
echo.

echo [2/2] Obtendo numero de serie...
echo.
powershell -Command "Get-ChildItem Cert:\LocalMachine\My | Where-Object {$_.Subject -like '*BRASCOPPER*'} | Format-List Subject, SerialNumber, NotAfter, Thumbprint"

echo.
echo =============================================
echo  Copie o SERIAL NUMBER e envie para o Emerson
echo =============================================
echo.
pause
