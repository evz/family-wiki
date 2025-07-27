# Requirements Files

This project uses separate requirements files for different environments:

## Production Requirements (`requirements.txt`)
Contains only the dependencies needed to run the application in production:
```bash
pip install -r requirements.txt
```

## Development Requirements (`requirements-dev.txt`)
Contains all production requirements plus development and testing tools:
```bash
pip install -r requirements-dev.txt
```

The development requirements file includes:
- Testing framework (pytest and plugins)
- Code quality tools (ruff)
- Development utilities

## Usage

**For development work:**
```bash
pip install -r requirements-dev.txt
```

**For production deployment:**
```bash
pip install -r requirements.txt
```

**For Docker builds:** Use the appropriate requirements file based on the target environment.