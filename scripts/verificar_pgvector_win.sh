echo 'Comandos para Windows (PowerShell):

cd D:\BRASC\PRG\06082025\pdd

REM Ver qual Python esta usando
where python
venv_django\Scripts\python -c "import pgvector; print('OK:' , pgvector.__version__)" 2>&1

REM Se falhar, instalar no venv
venv_django\Scripts\pip install pgvector

REM Testar de novo
venv_django\Scripts\python -c "import pgvector; print('OK:', pgvector.__version__)"
'
