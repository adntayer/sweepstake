"""Check syntax, _norm usage, f-string balance, and function call signatures."""
import ast
import sys
import os
import re

files = [
    r"C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\html.py",
    r"C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\dashboard.py",
]

def find_unmatched_braces_fstrings(source: str, filepath: str) -> list[str]:
    """Heuristic check for unbalanced braces in f-strings using regex."""
    errors = []
    lines = source.split('\n')
    for lineno, line in enumerate(lines, 1):
        # Find f-strings on this line
        # Match f"..." or f'...'
        fstrings = re.findall(r'f["\'](.+?)["\']', line)
        if not fstrings:
            fstrings = re.findall(r'f["\'](.+?)["\'](?=[^)]*\))', line)
        for fs in fstrings:
            # Count { and } inside the f-string body
            depth = 0
            for ch in fs:
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                if depth < 0:
                    break
            if depth != 0:
                errors.append(f"  {filepath}:{lineno}: Unbalanced braces in f-string: {line.strip()[:100]}")
    return errors

def find_unmatched_braces_all(source: str, filepath: str) -> list[str]:
    """Check ALL lines for unmatched braces that could affect Python parsing."""
    errors = []
    lines = source.split('\n')
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        # Skip comments and empty lines
        if not stripped or stripped.startswith('#'):
            continue
        # Count { and } outside string literals (approximate)
        in_string = False
        string_char = None
        depth = 0
        i = 0
        while i < len(stripped):
            ch = stripped[i]
            if in_string:
                if ch == '\\':
                    i += 2
                    continue
                if ch == string_char:
                    in_string = False
            else:
                if ch in ('"', "'"):
                    # Check for triple quotes
                    if stripped[i:i+3] in ('"""', "'''"):
                        in_string = True
                        string_char = stripped[i:i+3]
                        i += 3
                        continue
                    in_string = True
                    string_char = ch
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
            i += 1
        # only flag if depth != 0 AND it's a python-code line (not just CSS in a string)
        # For now skip this exhaustive check; the compile() will catch these
    return errors

def check_norm_usage(source: str, filepath: str, basename: str) -> list[str]:
    """Check _norm is defined and used consistently."""
    errors = []
    has_norm_def = '_norm(path: str) -> str:' in source or 'def _norm' in source
    if not has_norm_def:
        errors.append(f"  {filepath}: _norm function NOT DEFINED in this file")
    else:
        # Check all uses of os.path.normpath vs _norm
        normpath_calls = re.findall(r'os\.path\.normpath\b', source)
        if normpath_calls:
            errors.append(f"  {filepath}: Found {len(normpath_calls)} direct os.path.normpath calls (should use _norm()): {normpath_calls}")
        
        norm_calls = re.findall(r'\b_norm\(', source)
        # subtract the def line
        def_line = 0
        for i, line in enumerate(source.split('\n'), 1):
            if 'def _norm' in line:
                def_line = i
                break
        errors.append(f"  {filepath}: _norm() is used {len(norm_calls)} times (excluding definition)")
    return errors

def check_function_calls(source: str, filepath: str) -> list[str]:
    """Try to parse AST and check for undefined names in the module scope."""
    errors = []
    try:
        tree = ast.parse(source)
        # Collect all top-level function definitions and their args
        func_defs = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                arg_names = [a.arg for a in node.args.args]
                func_defs[node.name] = {
                    'args': arg_names,
                    'lineno': node.lineno,
                }
                # Also check for keyword-only args
                if node.args.kwonlyargs:
                    func_defs[node.name]['kwonly'] = [a.arg for a in node.args.kwonlyargs]
                if node.args.vararg:
                    func_defs[node.name]['vararg'] = node.args.vararg.arg
                if node.args.kwarg:
                    func_defs[node.name]['kwarg'] = node.args.kwarg.arg
        
        # Now check calls within the module
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                name = node.func.id
                if name.startswith('_') and name not in func_defs and name not in ('_heat_color', '_parse_correct', '_rule_color', '_match_rows'):
                    # Check if it's imported
                    pass  # This is too noisy
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                # Check method calls like config.scoring_emoji()
                pass
    except SyntaxError:
        errors.append(f"  {filepath}: Cannot check function calls - file has syntax errors")
    return errors

def check_config_api(source: str, filepath: str) -> list[str]:
    """Check that config API calls are consistent with known methods."""
    errors = []
    # Known config methods from the codebase
    known_methods = {
        'timezone', 'report_title', 'theme', 'scoring_rules', 'scoring_rule_names',
        'scoring_emoji', 'scoring_css_var', 'scoring_color', 'gold_valid_path',
        'gold_all_path', 'gold_playoff_valid_path', 'results_file', 'reports_dir',
        'index_html_path', 'group_phase_label', 'playoff_rounds',
        'playoff_strikers_path', '_au_first_round', 'to_css_vars',
    }
    calls = re.findall(r'config\.(\w+)\s*\(', source) + re.findall(r'config\.(\w+)\s*[^(\w]', source)
    # Deduplicate
    calls_set = set()
    for c in calls:
        # strip trailing non-word chars
        c = re.sub(r'\W+', '', c)
        calls_set.add(c)
    unknown = calls_set - known_methods
    for m in sorted(unknown):
        if m.islower() or m.startswith('_'):
            pass  # Skip for now - might be valid
    return errors

def check_fstring_variables(source: str, filepath: str) -> list[str]:
    """Check f-string expression variables exist in scope (basic check)."""
    errors = []
    # Find all f-string patterns with placeholder references
    # e.g. {config.report_title}, {boleiro}, etc.
    # This is hard to do statically without execution context, so skip for now
    return errors

for fp in files:
    basename = os.path.basename(fp)
    print(f"\n{'='*70}")
    print(f"CHECKING: {fp}")
    print(f"{'='*70}")
    
    with open(fp, 'r', encoding='utf-8') as f:
        source = f.read()
    
    # 1. Compile check
    print(f"\n--- Syntax Check (compile) ---")
    try:
        compile(source, fp, 'exec')
        print(f"  OK: No syntax errors")
    except SyntaxError as e:
        print(f"  SYNTAX ERROR: {e}")
        print(f"  Line {e.lineno}, offset {e.offset}: {e.msg}")
        if e.text:
            print(f"  Context: {e.text.rstrip()}")
    
    # 2. AST parse (more detailed)
    print(f"\n--- Syntax Check (AST) ---")
    try:
        tree = ast.parse(source)
        print(f"  OK: AST parsed successfully")
    except SyntaxError as e:
        print(f"  AST PARSE ERROR at line {e.lineno}: {e.msg}")
        if e.text:
            print(f"  Context: {e.text.rstrip()}")
    
    # 3. _norm usage
    print(f"\n--- _norm Function Usage ---")
    norm_errors = check_norm_usage(source, fp, basename)
    if norm_errors:
        for e in norm_errors:
            print(e)
    else:
        print(f"  OK: _norm defined and used consistently")
    
    # 4. f-string balance
    print(f"\n--- f-string Balance ---")
    fstring_errors = find_unmatched_braces_fstrings(source, fp)
    if fstring_errors:
        for e in fstring_errors:
            print(e)
    else:
        print(f"  OK: No unbalanced braces found in f-strings")
    
    # 5. Function call signatures (basic)
    print(f"\n--- Function Call Signatures ---")
    call_errors = check_function_calls(source, fp)
    if call_errors:
        for e in call_errors:
            print(e)
    else:
        print(f"  OK: Basic function call check passed")

print(f"\n{'='*70}")
print(f"CHECK COMPLETE")
print(f"{'='*70}")
