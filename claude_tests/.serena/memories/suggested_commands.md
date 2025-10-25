# Suggested Commands

## Testing Commands

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest test_filename.py
```

### Run tests with specific environment
```bash
pytest --env stg test_filename.py
```

### Run tests with verbose output
```bash
pytest -v test_filename.py
```

### Run specific test function
```bash
pytest test_filename.py::test_function_name
```

### Run tests with output capture disabled (see print statements)
```bash
pytest -s test_filename.py
```

## Windows-Specific Shell Commands

### File System Operations
```cmd
dir                    # List directory contents
cd <path>              # Change directory
mkdir <dirname>        # Create directory
rmdir /s <dirname>     # Remove directory and contents
del <filename>         # Delete file
type <filename>        # Display file contents
copy <src> <dest>      # Copy file
move <src> <dest>      # Move file
```

### Search Operations
```cmd
dir /s /b *.py         # Find all .py files recursively
findstr "pattern" file # Search for pattern in file
```

### Environment Variables
```cmd
set                    # List all environment variables
set VAR=value          # Set environment variable
echo %VAR%             # Display environment variable
```

## Python Commands

### Install dependencies (if requirements.txt exists)
```bash
pip install -r requirements.txt
```

### Install Playwright browsers
```bash
playwright install chromium
```

## Git Commands (if using version control)
```bash
git status
git add .
git commit -m "message"
git push
git pull
```

## Notes
- Most commands should work in PowerShell, Command Prompt, or Git Bash
- Tests assume Playwright is already installed
- Environment variables should be set in `.env` file (not checked into version control)
