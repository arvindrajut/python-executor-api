from flask import Flask, request, jsonify
import os
import subprocess
import json
import signal
import tempfile
import shutil

app = Flask(__name__)

PYTHON_BINARY = '/usr/bin/python3'

@app.route('/execute', methods=['POST'])
def execute():
    data = request.get_json()
    if not data or 'script' not in data:
        return jsonify({'error': 'Missing "script" in request body'}), 400

    script = data['script']
    if 'def main' not in script:
        return jsonify({'error': 'Script must contain a main() function'}), 400

    # Create a temporary directory for this execution
    temp_dir = tempfile.mkdtemp(prefix='python_exec_')
    script_path = os.path.join(temp_dir, 'script.py')
    
    try:
        with open(script_path, 'w') as f:
            f.write(script)

        # Use subprocess with timeout and resource limits
        cmd = [PYTHON_BINARY, script_path]
        
        # Set resource limits using ulimit-like approach
        def preexec_fn():
            # Set CPU time limit (5 seconds)
            import resource
            resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
            # Set memory limit (512 MB)
            resource.setrlimit(resource.RLIMIT_AS, (512*1024*1024, 512*1024*1024))
            # Set file size limit (10 MB)
            resource.setrlimit(resource.RLIMIT_FSIZE, (10*1024*1024, 10*1024*1024))
            # Set number of open files limit
            resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
            # Change to a restricted directory
            os.chdir(temp_dir)
        
        result = subprocess.run(
            cmd,
            capture_output=True, 
            text=True, 
            timeout=10,
            preexec_fn=preexec_fn,
            cwd=temp_dir
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
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)