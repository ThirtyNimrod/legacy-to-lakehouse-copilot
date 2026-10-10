# Run automated tests
.\.venv\Scripts\pytest -v tests/

# Run CLI workflow
.\.venv\Scripts\python.exe -m src.cli seed
.\.venv\Scripts\python.exe -m src.cli run --table raw_orders --thread-id demo01
.\.venv\Scripts\python.exe -m src.cli resume --thread-id demo01 --action approve
