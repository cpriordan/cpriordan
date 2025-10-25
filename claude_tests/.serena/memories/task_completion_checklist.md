# Task Completion Checklist

When completing any task in this project, follow this checklist:

## 1. Code Quality
- [ ] Code follows snake_case naming conventions
- [ ] Type hints added to function signatures
- [ ] Docstrings added for classes and complex functions
- [ ] Comments added for non-obvious logic
- [ ] No hardcoded credentials (use environment variables)

## 2. Testing
- [ ] Test function names start with `test_`
- [ ] Fixtures properly scoped
- [ ] Async functions properly use `async/await`
- [ ] Proper error handling with timeouts
- [ ] Screenshots saved to correct directory structure

## 3. Environment Configuration
- [ ] Environment variables properly loaded from `.env`
- [ ] Validation for required environment variables
- [ ] Clear error messages for missing configuration

## 4. Before Committing
- [ ] Run relevant tests to ensure they pass
- [ ] Review test output for any unexpected errors
- [ ] Check screenshot directories created correctly
- [ ] Verify environment-specific logic works (STG/PROD)

## 5. Documentation
- [ ] Update CLAUDE.md if significant patterns change
- [ ] Add comments explaining complex test scenarios
- [ ] Document any new environment variables needed

## No Linting/Formatting Tools Configured
⚠️ **Note**: This project does not appear to have configured linting or formatting tools (no black, flake8, pylint, mypy configuration found). However, you should still:
- Follow PEP 8 style guidelines manually
- Keep line lengths reasonable
- Use consistent indentation (4 spaces)
- Format imports properly (standard lib, third-party, local)

## Testing Workflow
1. Write or modify test code
2. Run the specific test: `pytest test_filename.py -v`
3. Check for errors and fix as needed
4. Verify screenshots are generated correctly
5. Test with both STG and PROD environments if applicable
