# Project Python Style Guide for Gemini Code Assist

This document outlines the preferred coding style, architectural principles, and general best practices for Python code within this repository. Gemini Code Assist should adhere to these guidelines when generating or modifying code to ensure consistency, readability, and maintainability.

## 1. General Philosophy

* **Pythonic:** Prioritize idiomatic Python code.
* **Readability:** Code should be easy to read and understand at a glance. Clarity over cleverness.
* **Maintainability:** Code should be easy to modify, debug, and extend.
* **Testability:** Code should be designed with testing in mind, making unit and integration tests straightforward.
* **Single Responsibility Principle (SRP):** This is paramount. Every function, method, and class should have one, and only one, reason to change.

## 2. Naming Conventions

Adhere strictly to [PEP 8 -- Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/#naming-conventions).

* **Modules:** `lowercase_with_underscores` (e.g., `user_service.py`).
* **Packages:** `lowercase_with_no_underscores`.
* **Classes:** `CapWords` (e.g., `UserManager`, `DatabaseConnector`).
* **Functions & Variables:** `snake_case` (e.g., `get_user_by_id`, `user_data`).
* **Constants:** `UPPER_CASE_WITH_UNDERSCORES` (e.g., `MAX_RETRIES`, `DEFAULT_TIMEOUT_SECONDS`).
* **Private/Protected Members:** `_single_leading_underscore` for internal-use methods/attributes (convention, not strict enforcement). `__double_leading_underscore` should be avoided unless strictly necessary for name mangling.

## 3. Code Structure: Functions & Methods

* **Single Responsibility Principle (SRP):** Each function/method must perform a single, well-defined task. If a function description uses "and" to connect multiple actions, it likely violates SRP.
* **Length (Guideline, not Strict Rule):**
    * Aim for functions to be concise, ideally fitting within a single screen view.
    * Prefer functions to be **under 40 lines of executable code** (excluding docstrings, comments, and simple assignments).
    * **Orchestration Functions:** Functions that solely coordinate calls to other, smaller functions (e.g., a `process_user_registration` function calling `validate_input`, `create_db_record`, `send_email`) are an **exception** to the line limit. Their responsibility is orchestration, and their length is determined by the number of steps in the workflow. They should still primarily consist of high-level calls.
* **Level of Abstraction:** All statements within a function should operate at the same level of abstraction. Do not mix high-level business logic with low-level details (e.g., database queries or complex string parsing) in the same function. Extract lower-level details into separate helper functions.
* **Parameters:** Limit the number of parameters to a maximum of **5**. For more complex input, consider passing a `dataclass` or `TypedDict` object.
* **Return Values:** Functions should typically return a single, consistent type or structure. Avoid returning different types based on different execution paths if possible.

## 4. Code Structure: Classes

* **Single Responsibility Principle (SRP):** Each class should have a single, clear, and well-defined responsibility. Avoid "God objects" that manage too many concerns.
* **Cohesion:** Methods within a class should be highly related and work together towards the class's single responsibility.
* **Coupling:** Aim for loose coupling between classes. Use dependency injection to provide dependencies rather than creating them internally where possible.
* **Small Classes:** Prefer many small, focused classes over a few large, monolithic ones.
* **__init__ method:** Keep `__init__` methods concise, primarily for assigning instance variables. Complex setup logic should be delegated to other methods.

## 5. Code Structure: Modules & Packages

* **Logical Grouping:** Group related classes, functions, and constants into logical modules (`.py` files).
* **Single Responsibility Principle (SRP):** Just like classes and functions, each module (`.py` file) should have a single, well-defined responsibility. For example, a file might handle database interactions for a specific model (`user_repository.py`), define application-specific exceptions (`exceptions.py`), or contain utility functions for a particular domain (`string_utils.py`).
* **Clear Boundaries:** Packages should define clear functional boundaries (e.g., `services/`, `models/`, `utils/`, `api/`).
* **Constants File:** All project-wide constants (used in more than one module) **must** be defined in a dedicated `constants.py` file in the root of the relevant package.
* **Utility Modules:** Generic, widely applicable helper functions should reside in a `utils.py` module. Specific helper functions relevant to a single module should live within that module.
* **Avoid Circular Dependencies:** Be mindful of import loops between modules.

## 6. Readability & Documentation

* **Docstrings:** All public functions, methods, and classes **must** have clear and concise docstrings following [PEP 257](https://www.python.org/dev/peps/pep-0257/).
    * For functions/methods: Describe purpose, arguments (`Args:`), and return value (`Returns:`).
    * For classes: Describe its purpose and main responsibilities.
* **Comments:** Comments should explain *why* a piece of code is written in a particular way, not *what* it does (good code should be self-documenting for the "what"). Avoid redundant comments.
* **Type Hinting:** Use type hints extensively for all function parameters, return values, and instance variables (PEP 484). This significantly improves readability and enables static analysis.
* **Consistent Formatting:** Adhere to PEP 8 whitespace conventions (e.g., 4 spaces for indentation). Use a formatter like `black` or `autopep8` for automated formatting to ensure consistency.

## 7. Error Handling

* **Specific Exceptions:** Prefer raising and catching specific, custom exception types over generic `Exception` where appropriate.
* **Graceful Degradation:** Design functions to handle expected errors gracefully, providing informative error messages or fallback mechanisms.
* **Logging:** Use Python's standard `logging` module for all logging needs (info, debug, warning, error, critical). Avoid using `print()` for debugging or logging in production code.

## 8. Imports

* **Absolute Imports:** Prefer absolute imports (e.g., `from my_project.services import user_service`) over relative imports for modules outside the current package.
* **Relative Imports:** Use relative imports for modules within the same package (e.g., `from . import utils`).
* **Ordering:** Follow PEP 8 import ordering:
    1.  Standard library imports.
    2.  Third-party imports.
    3.  Local application/library specific imports.
    Each group should be separated by a blank line and sorted alphabetically.

## 9. Specific Practices & Anti-Patterns to Avoid

* **Avoid `from module import *`:** Do not use star imports as they obscure the origin of names and can lead to namespace clashes.
* **Minimize Global Variables:** Avoid using mutable global variables. Pass data explicitly through function parameters.
* **List/Dict Comprehensions:** Prefer list, dict, and set comprehensions over traditional `for` loops when they improve conciseness and readability for simple transformations.
* **No Magic Numbers/Strings:** All "magic" values should be defined as named constants.

---