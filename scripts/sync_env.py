import os
import shutil

def parse_env(file_path):
    """Parses an environment file into a dictionary."""
    env_vars = {}
    if not os.path.exists(file_path):
        return env_vars
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    return env_vars

def write_env(file_path, env_vars, source_path=None):
    """Writes environment variables to a file, preserving comments if source exists."""
    lines = []
    
    # keys that should NOT be overwritten in local .env if they differ from docker
    # We want local dev to use localhost, while docker uses service names
    PROTECTED_KEYS = {
        "POSTGRES_HOST": '"localhost"',
        "POSTGRES_PORT": '"5433"',
    }

    if source_path and os.path.exists(source_path):
        with open(source_path, 'r', encoding='utf-8') as f:
            source_lines = f.readlines()
        
        # Determine strict key order and comments from source
        # This is complex to do perfectly without a parser library, 
        # so we'll just append new keys to the end or update existing ones if we read line by line.
        
        # Simplified approach: Read source, update values in memory, write back.
        # But we need to handle the case where keys are MISSING in source (local .env) but present in master (env.app)
        
        # Let's just create a merged dictionary first
        merged_vars = env_vars.copy()
        
        # Apply protected keys for local dev environment
        if "SRC/.env" in file_path:
             for k, v in PROTECTED_KEYS.items():
                 merged_vars[k] = v
        
        with open(file_path, 'w', encoding='utf-8') as f:
            # We will read the TARGET file (if it exists) to preserve its comments/structure? 
            # Or the MASTER file (env.app) to enforce structure?
            # Let's enforce structure from env.app (source_path)
            
            for line in source_lines:
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    f.write(line)
                    continue
                
                if '=' in stripped:
                    key = stripped.split('=', 1)[0].strip()
                    if key in merged_vars:
                        f.write(f'{key} = {merged_vars[key]}\n')
                        del merged_vars[key] # Mark as written
                    else:
                        # Key in env.app but not in our vars? (Shouldn't happen if we parsed env.app)
                        f.write(line)
            
            # Write any remaining keys (new ones added to env.app since last sync?)
            if merged_vars:
                f.write("\n# --- New Variables ---\n")
                for key, value in merged_vars.items():
                    f.write(f'{key} = {value}\n')

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    docker_env_path = os.path.join(root_dir, 'Docker', 'env', '.env.app')
    local_env_path = os.path.join(root_dir, 'SRC', '.env')
    example_env_path = os.path.join(root_dir, 'SRC', '.env.example')

    print(f"Syncing environment variables...")
    print(f"Source (Docker): {docker_env_path}")
    print(f"Target (Local):  {local_env_path}")

    if not os.path.exists(docker_env_path):
        print(f"Error: Source file {docker_env_path} not found.")
        return

    # 1. Read Docker env (Master)
    master_vars = parse_env(docker_env_path)

    # 2. Update Local .env
    # We want to keep local config if it exists, but add missing keys.
    # AND enforce structure of docker env.
    
    # Actually, simpler logic: 
    # Take Docker env, replace HOST/PORT with localhost/5433, write to SRC/.env
    # allowing user to keep their secrets if we cared, but here we assume env.app has the "truth"
    # except secrets might be placeholders.
    
    # If SRC/.env exists, we should probably respect its values for secrets??
    # The prompt asked to "update the env file based on the env.app file". 
    # Usually env.app implies "application defaults" and local .env has "overrides/secrets".
    # But for a dev setup often they are identical except for hostnames.
    
    write_env(local_env_path, master_vars, source_path=docker_env_path)
    print(f"Updated {local_env_path}")

    # 3. Update .env.example
    # Just copy env.app structure but value placeholders? 
    # For now, let's just make it identical to env.app (often safe for examples)
    shutil.copy(docker_env_path, example_env_path)
    print(f"Updated {example_env_path}")

if __name__ == "__main__":
    main()
