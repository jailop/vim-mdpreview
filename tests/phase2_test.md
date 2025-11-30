# Phase 2 Features Test

## Wiki-Links

Regular wiki-links: [[another-note]] and [[some-page|Custom Text]]

## File Inclusion

Including another file:

[[!tests/sample-include]]

Including with custom title:

[[!tests/sample-include|Custom Title for Inclusion]]

## LaTeX Formulas

### Inline Math

The quadratic formula is $x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$.

Einstein's famous equation: $E = mc^2$.

### Block Math

Display formulas:

$$
\int_{a}^{b} f(x) dx = F(b) - F(a)
$$

And another one:

$$
\sum_{i=1}^{n} i = \frac{n(n+1)}{2}
$$

## Code Syntax Highlighting

### Python Code

```python
def fibonacci(n):
    """Calculate Fibonacci number recursively"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Test it
for i in range(10):
    print(f"F({i}) = {fibonacci(i)}")
```

### JavaScript Code

```javascript
// Arrow function example
const greet = (name) => {
    return `Hello, ${name}!`;
};

// Async/await
async function fetchData(url) {
    try {
        const response = await fetch(url);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error:', error);
    }
}
```

### C++ Code

```cpp
#include <iostream>
#include <vector>

// Template function
template<typename T>
T max(T a, T b) {
    return (a > b) ? a : b;
}

int main() {
    std::vector<int> numbers = {1, 2, 3, 4, 5};
    
    for (const auto& num : numbers) {
        std::cout << num << " ";
    }
    
    return 0;
}
```

## Combined Features

Here's a wiki-link with LaTeX: See [[math-notes]] for more on $\pi = 3.14159...$

## Tables

| Feature | Status | Notes |
|---------|--------|-------|
| Wiki-links | ✅ | Working |
| File Inclusion | ✅ | Working |
| LaTeX | ✅ | Working |
| Syntax Highlighting | ✅ | Working |

## Task Lists

- [x] Implement wiki-links
- [x] Implement file inclusion
- [x] Implement LaTeX rendering
- [x] Implement syntax highlighting
- [ ] Add theme support
- [ ] Add export features
