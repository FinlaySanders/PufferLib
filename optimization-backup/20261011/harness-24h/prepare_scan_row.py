from pathlib import Path
import difflib

root = Path(__file__).resolve().parent
p = root / 'source/src/algo.cu'
before = p.read_text()
s = before
condition = '''if (scan.T >= 256 && scan.B * scan.H <= 32768
                || scan.T >= 128 && scan.H <= 32) {'''
assert s.count(condition) == 2
for bit in [1, 2]:
    replacement = '''if ((getenv("PUF_SCAN_ROW") && (atoi(getenv("PUF_SCAN_ROW")) & %d))
                || scan.T >= 256 && scan.B * scan.H <= 32768
                || scan.T >= 128 && scan.H <= 32) {''' % bit
    s = s.replace(condition, replacement, 1)
p.write_text(s)
(root/'scan_row.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='a/src/algo.cu',tofile='b/src/algo.cu')))
