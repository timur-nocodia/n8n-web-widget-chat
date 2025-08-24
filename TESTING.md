# Testing Guide - n8n Chat Widget

This guide covers all testing approaches for the n8n Chat Widget system, including PyLint code quality analysis, functional testing, and deployment validation.

## 📋 Table of Contents

- [PyLint Code Quality Testing](#-pylint-code-quality-testing)
- [Functional Testing](#-functional-testing)
- [Security Testing](#-security-testing)
- [Performance Testing](#-performance-testing)
- [Docker Testing](#-docker-testing)
- [CI/CD Testing](#-cicd-testing)

## 🔍 PyLint Code Quality Testing

### Quick Setup

```bash
# Create virtual environment and install PyLint
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install pylint

# Install project dependencies
pip install --only-binary=all fastapi uvicorn pydantic httpx python-dotenv pyjwt
```

### Basic PyLint Testing

```bash
# Navigate to proxy server directory
cd apps/proxy-server

# Run basic analysis (recommended)
python test_pylint.py

# Example output:
# 🔍 Running Basic PyLint Analysis...
# 📄 Analyzing main_stateless.py...
# 📊 Score: 8.02/10
# ✅ No high priority issues found
# 📈 Average Score: 8.14/10
# 🎉 Excellent code quality!
```

### Advanced PyLint Testing

```bash
# Show fixable issues
python test_pylint.py --fix

# Run detailed analysis (shows all issues)
python test_pylint.py --detailed

# CI/CD mode (exits with error code if quality is low)
python test_pylint.py --ci
```

### Manual PyLint Commands

```bash
# Test specific files
source venv/bin/activate
pylint main_stateless.py --disable=import-error
pylint main_production.py --disable=import-error,too-few-public-methods
pylint main_sqlite.py --disable=import-error

# Generate reports
pylint main_stateless.py --output-format=json > pylint_report.json
pylint main_stateless.py --output-format=html > pylint_report.html
```

### PyLint Score Interpretation

- **9.0-10.0**: Excellent code quality
- **8.0-8.9**: Good code quality  
- **7.0-7.9**: Acceptable code quality
- **6.0-6.9**: Needs improvement
- **<6.0**: Significant issues need attention

### Common PyLint Issues and Fixes

**Trailing whitespace (C0303)**:
```bash
# Fix automatically
sed -i '' 's/[[:space:]]*$//' main_stateless.py
```

**Line too long (C0301)**:
```python
# Before (too long)
very_long_function_call_with_many_parameters(param1, param2, param3, param4, param5)

# After (fixed)
very_long_function_call_with_many_parameters(
    param1, param2, param3, 
    param4, param5
)
```

**Logging f-string interpolation (W1203)**:
```python
# Before (problematic)
logger.info(f"Processing session {session_id}")

# After (fixed)
logger.info("Processing session %s", session_id)
```

## 🧪 Functional Testing

### Manual Widget Testing

```bash
# Start server
source venv/bin/activate
python main_stateless.py

# Test URLs
open http://localhost:8000/widget/modern-widget.html
open http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/session/create
```

### API Testing with curl

```bash
# Health check
curl -f http://localhost:8000/health

# Create session
curl -X POST http://localhost:8000/api/v1/session/create \
  -H "Content-Type: application/json" \
  -d '{"origin_domain": "localhost"}'

# Test streaming (requires session cookie)
curl -N http://localhost:8000/api/v1/chat/stream/your-session-id \
  -H "Cookie: chat_session_id=your-session-cookie"
```

### Browser Testing Checklist

- [ ] Widget loads without console errors
- [ ] Chat messages send and receive properly  
- [ ] SSE streaming works in real-time
- [ ] Unread message notifications appear
- [ ] Session persists across page reloads
- [ ] Widget is transparent when embedded
- [ ] Responsive design works on mobile

## 🔒 Security Testing

### Rate Limiting Test

```bash
# Test rate limits (should be blocked after limit)
for i in {1..70}; do
  curl -X POST http://localhost:8000/api/v1/session/create
  echo "Request $i"
done
```

### CORS Testing

```bash
# Test CORS restrictions
curl -H "Origin: https://unauthorized.com" \
  -X POST http://localhost:8000/api/v1/session/create

# Should return CORS error
```

### Input Sanitization Testing

```bash
# Test XSS prevention
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "<script>alert(\"xss\")</script>"}'
```

## ⚡ Performance Testing

### Load Testing with Apache Bench

```bash
# Install apache bench (ab)
# macOS: brew install httpie
# Ubuntu: sudo apt-get install apache2-utils

# Test session creation
ab -n 100 -c 10 -H "Content-Type: application/json" \
  -p session_data.json \
  http://localhost:8000/api/v1/session/create

# Create session_data.json
echo '{"origin_domain": "localhost"}' > session_data.json
```

### Memory and CPU Monitoring

```bash
# Monitor server resources
top -pid $(pgrep -f "python main_")

# Memory usage
ps -o pid,vsz,rss,comm -p $(pgrep -f "python main_")
```

## 🐳 Docker Testing

### Docker Compose Testing

```bash
# Build and test
docker-compose build
docker-compose up -d

# Test health
curl -f http://localhost:8000/health

# View logs  
docker-compose logs -f chat-proxy

# Cleanup
docker-compose down
```

### Docker Security Testing

```bash
# Test container security
docker run --rm -it \
  -v $(pwd):/app \
  -w /app \
  python:3.11-slim \
  /bin/bash -c "pip install safety && safety check -r requirements-stateless.txt"
```

## 🚀 CI/CD Testing

### GitHub Actions Test Script

```yaml
name: Quality Tests
on: [push, pull_request]

jobs:
  pylint:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      working-directory: apps/proxy-server
      run: |
        python -m venv venv
        source venv/bin/activate
        pip install pylint fastapi uvicorn pydantic httpx python-dotenv pyjwt
    
    - name: Run PyLint
      working-directory: apps/proxy-server  
      run: |
        source venv/bin/activate
        python test_pylint.py --ci
```

### Pre-commit Hook

```bash
# Create .git/hooks/pre-commit
#!/bin/bash
cd apps/proxy-server
source venv/bin/activate
python test_pylint.py --ci

if [ $? -ne 0 ]; then
  echo "PyLint checks failed. Commit aborted."
  exit 1
fi
```

## 📊 Test Reports and Metrics

### Generate PyLint Reports

```bash
source venv/bin/activate

# JSON report
pylint main_stateless.py --output-format=json > reports/pylint_stateless.json

# HTML report  
pylint main_stateless.py --output-format=html > reports/pylint_stateless.html

# Text report with metrics
pylint main_stateless.py --reports=yes > reports/pylint_detailed.txt
```

### Coverage Analysis (if tests exist)

```bash
# Install coverage
pip install coverage pytest

# Run with coverage
coverage run -m pytest
coverage report -m
coverage html  # Generates htmlcov/index.html
```

## 🐛 Common Testing Issues and Solutions

### PyLint Not Found

```bash
# Solution: Install in virtual environment
python -m venv venv
source venv/bin/activate
pip install pylint
```

### Import Errors in PyLint

```bash
# Solution: Install dependencies or disable import-error
pip install -r requirements-stateless.txt
# OR
pylint main_stateless.py --disable=import-error
```

### SSE Testing Issues

```bash
# Use curl with -N flag for streaming
curl -N http://localhost:8000/api/v1/chat/stream/session-id

# Check server logs for streaming issues
tail -f server.log
```

### Docker Build Issues

```bash
# Clear Docker cache
docker system prune -a

# Build with no cache
docker-compose build --no-cache
```

## 🎯 Testing Best Practices

1. **Automated Testing**: Use the `test_pylint.py` script for consistent results
2. **Regular Testing**: Run PyLint before every commit
3. **Score Tracking**: Maintain score above 8.0/10 for production code
4. **Fix Priorities**: Address errors (E) and warnings (W) before conventions (C)
5. **CI Integration**: Use `--ci` mode in automated pipelines
6. **Documentation**: Keep TESTING.md updated with new test procedures

## 📚 Additional Resources

- **PyLint Documentation**: https://pylint.pycqa.org/
- **FastAPI Testing**: https://fastapi.tiangolo.com/tutorial/testing/
- **Docker Testing**: https://docs.docker.com/develop/dev-best-practices/
- **Performance Testing**: https://docs.locust.io/

---

**Next Steps**: After running PyLint tests, proceed with functional testing and then Docker deployment validation.