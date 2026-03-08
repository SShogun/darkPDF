# Testing if darkmode dumps to console
import darkmode
import sys
from io import StringIO

print("Start test")
darkmode.generate_dark_pdf("tests/test.pdf", "tests/test_output.pdf", 0.5)
print("End test")
