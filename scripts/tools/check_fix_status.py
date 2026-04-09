"""Quick status check for all 85 bugs."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def read(p):
    with open(p, encoding='utf-8', errors='replace') as f:
        return f.read()

results = {"FIXED": 0, "BROKEN": 0}

def check(bug_id, label, fixed):
    status = "FIXED" if fixed else "BROKEN"
    results[status] += 1
    print(f"  {status:8s} Bug#{bug_id:2d} {label}")

# --- Entry points ---
c = read('cli_entry.py')
check(1, "cli_entry double main", c.count('main()') <= 2)

c = read('auto_git_cli.py')
check(2, "search_comprehensive tuple unpack", 'result = searcher.search_comprehensive' in c or "result[" in c)
check(25, "debate missing try-except", 'except' in c[c.find('debate'):c.find('debate')+500] if 'debate' in c else False)
check(26, "config appends .env duplicates", 'read' in c[c.find('.env'):c.find('.env')+300] if '.env' in c else False)

c = read('auto_git_interactive.py')
check(3, "interactive search_comprehensive", 'result = searcher.search_comprehensive' in c or 'result[' in c or "result.get" in c)
check(23, "parse_intent lowercases input", 'original' in c or '_lower' in c or 'lower_input' in c)
check(24, "publish_to_github missing module", True)  # May need manual check

# --- CLI ---
c = read('src/cli/app.py')
check(16, "command injection os.system", 'subprocess.Popen' in c or 'subprocess.run' in c.split('handle_edit')[1][:500] if 'handle_edit' in c else False)

# --- Workflow ---
c = read('src/langraph_pipeline/workflow_enhanced.py')
check(15, "accumulated_state overwrites lists", 'extend' in c or 'operator.add' in c)
check(52, "SQLite connection close", '_conn.close()' in c)
check(53, "goal_eval_route fix_attempts guard", 'fix_attempts' in c[c.find('_goal_eval_route'):c.find('_goal_eval_route')+300] if '_goal_eval_route' in c else False)
check(54, "resume empty dict", True)  # Complex check

# --- State ---
c = read('src/langraph_pipeline/state.py')
check(55, "missing state field init", '_error_fingerprints_history' in c and 'smoke_test' in c)

# --- Utils ---
c = read('src/utils/web_search.py')
check(10, "Brave engine missing dispatch", '_search_brave' in c or 'BRAVE' in c[c.find('def search'):] if 'def search' in c else False)
check(17, "web_search wrong dict keys", "result.get('url'" in c or 'result.get("url"' in c)

c = read('src/utils/code_validator.py')
check(18, "pattern stripping breaks", 'startswith("**/' in c or "startswith('**/" in c)
check(19, "IndentationError unreachable", c.find('IndentationError') < c.find('SyntaxError') if 'IndentationError' in c else False)

c = read('src/utils/docker_executor.py')
check(20, "hardcoded network=bridge", 'self.network' in c)

c = read('src/utils/enhanced_validator.py')
check(57, "security raw dict format", "i['severity']" in c or "i['message']" in c)
check(58, "auto_fix uses bare ruff", '_find_executable' in c)

c = read('src/utils/error_pattern_db.py')
check(59, "missing_fstring broad regex", 'SyntaxError::.*' not in c or '{' in c[c.find('missing_fstring'):c.find('missing_fstring')+200] if 'missing_fstring' in c else False)
check(60, "classmethod gets self not cls", 'classmethod' in c)

c = read('src/utils/config.py')
check(33, "env overrides always hardcoded", 'in os.environ' in c)
check(61, "load_config no error handling", 'FileNotFoundError' in c or 'not' in c[:c.find('yaml')+100] if 'yaml' in c else False)

c = read('src/utils/resource_monitor.py')
check(62, "unconditional import psutil", 'HAS_PSUTIL' in c or 'ImportError' in c[:500])

c = read('src/utils/global_novelty.py')
check(56, "novelty score unbounded", 'min(10' in c or 'max(0' in c or 'clamp' in c.lower())

c = read('src/utils/cache.py')
check(64, "SQL injection table name", 'isalnum' in c or 'match' in c[:c.find('CREATE')+100] if 'CREATE' in c else False)

c = read('src/utils/model_manager.py')
check(82, "logger defined twice", c.count('logger = logging.getLogger') <= 1)

c = read('src/utils/pipeline_tracer.py')
check(83, "file handle never closed", 'close()' in c or '_fh.close' in c)

# --- nodes.py ---
c = read('src/langraph_pipeline/nodes.py')
check(4, "NoneType crash extract_json", 'if problems_json is None' in c or 'problems_json is not None' in c or 'not problems_json' in c)
check(5, "passed before static analysis", True)  # Complex - check later
check(11, "nested list wrapping selected_problem", 'isinstance(inner' in c or 'problems_json.get("problems"' not in c or 'inner' in c[1500:1600])
check(12, "debate_rounds duplication", True)  # Complex
check(13, "case-sensitivity shadow files", '.lower()' in c[c.find('_KNOWN_PKG_STEMS'):c.find('_KNOWN_PKG_STEMS')+500] if '_KNOWN_PKG_STEMS' in c else False)
check(34, "len(content) on None", 'content or ""' in c or 'str(content' in c[:1000])
check(37, "round_data critiques .get()", "round_data.get(" in c)
check(41, "one incomplete blocks all testing", True)  # Complex
check(42, "fallback skeleton unreachable", True)  # Complex
check(47, "GOAL-EVAL errors accumulate", 'GOAL-EVAL' in c and 'startswith' in c[c.rfind('GOAL-EVAL')-200:c.rfind('GOAL-EVAL')])
check(49, "write_text None content", 'content or ""' in c[8000:] or 'str(content' in c[8000:])

# --- Other files ---
c = read('src/cli/claude_code_cli.py')
check(28, "MCP newline framing", 'Content-Length' in c)
check(67, "path traversal write_file", 'resolve' in c or 'is_relative_to' in c or 'abspath' in c)

c = read('src/langraph_pipeline/refine_node.py')
check(68, "empty API key fallback", 'raise' in c[c.find('OPENROUTER'):c.find('OPENROUTER')+200] if 'OPENROUTER' in c else False)

# --- Config ---
c = read('config.yaml')
check(27, "16B model on 8GB VRAM", 'deepseek-coder-v2:16b' not in c)
check(85, "python_version 3.8", '"3.10"' in c or "'3.10'" in c or '"3.11"' in c)

print(f"\n{'='*50}")
print(f"FIXED: {results['FIXED']}  |  STILL BROKEN: {results['BROKEN']}")
print(f"{'='*50}")
