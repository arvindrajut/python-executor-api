from flask import Flask, request, jsonify
import os
import subprocess
import json

app = Flask(__name__)

NSJAIL_BINARY = '/usr/bin/nsjail'
PYTHON_BINARY = '/usr/bin/python3'

@app.route('/execute', methods=['POST'])
def execute():
    data = request.get_json()
    if not data or 'script' not in data:
        return jsonify({'error': 'Missing "script" in request body'}), 400

    script = data['script']
    if 'def main' not in script:
        return jsonify({'error': 'Script must contain a main() function'}), 400

    script_path = '/sandbox/script.py'
    with open(script_path, 'w') as f:
        f.write(script)

    try:
        # Use command line arguments instead of config file - more compatible for Cloud Run
        cmd = [
            NSJAIL_BINARY,
            '--mode', 'o',  # ONCE mode
            '--exec_file', PYTHON_BINARY,
            '--cwd', '/sandbox',
            '--bindmount', '/sandbox:/sandbox',
            '--time_limit', '10',
            '--rlimit_as', '512',
            '--rlimit_cpu', '5',
            '--rlimit_fsize', '10',
            '--rlimit_nofile', '32',
            '--disable_clone_newnet',
            '--disable_clone_newuser',  # Disable user namespace - often problematic in containers
            '--disable_clone_newcgroup',  # Disable cgroup namespace - may not be available
            '--disable_clone_newuts',  # Disable UTS namespace
            '--disable_clone_newipc',  # Disable IPC namespace
            '--keep_caps',  # Keep capabilities to avoid securebits issues
            '--disable_no_new_privs',  # Disable NO_NEW_PRIVS to avoid prctl issues
            '--',
            'script.py'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        if result.returncode != 0:
            return jsonify({'error': 'Script execution failed', 'stderr': result.stderr}), 400

        if not result.stdout.strip():
            return jsonify({'error': 'Script produced no output'}), 400

        last_line = result.stdout.strip().splitlines()[-1]
        try:
            result_json = json.loads(last_line)
        except json.JSONDecodeError:
            return jsonify({'error': 'main() did not return a valid JSON object'}), 400

        return jsonify({'result': result_json, 'stdout': result.stdout})
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Script execution timed out'}), 408
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)