# AWE Test Rig - Documentation

This directory contains comprehensive documentation for the AWE Electrolyzer Test Rig software.

## 📚 Available Documentation

### [Standardized Logging System](standardized_logging.md)
**Complete guide for developers** on using the standardized logging system throughout the codebase.

- **Quick Start:** Import and basic usage
- **Log Levels:** INFO, SUCCESS, WARNING, ERROR with examples
- **Component Naming:** Conventions and best practices
- **Real-World Patterns:** Service startup, configuration loading, hardware connection
- **Migration Guide:** Converting existing print statements
- **Quick Reference:** Cheat sheet for common usage

### [Post Processing](post_processing.md)
Guide for data analysis and plot generation after test sessions.

---

## 🚀 For New Developers

**Start here for consistent, professional logging:**

1. Read the [Standardized Logging Guide](standardized_logging.md)
2. Import the logger: `from utils.logger import log`
3. Use appropriate log levels: `log.info()`, `log.success()`, `log.warning()`, `log.error()`
4. Follow component naming conventions
5. Use structured sublines for detailed information

**Example:**
```python
from utils.logger import log

log.success("Hardware", "Sensors initialized", [
    "• Temperature: 8 channels",
    "• Pressure: 6 channels", 
    "→ All systems ready"
])
```

**Output:**
```
[2025-08-01 12:08:30] SUCCESS  [Hardware]     - Sensors initialized
    • Temperature: 8 channels
    • Pressure: 6 channels
    → All systems ready
```

---

## 📖 Contributing to Documentation

When adding new features or modules:

1. **Update relevant documentation** if your changes affect existing guides
2. **Add new documentation** for significant new features
3. **Follow the same format** as existing documentation
4. **Update this index** when adding new documentation files

---

*For technical architecture details, see the main [architecture.md](../architecture.md) file.* 