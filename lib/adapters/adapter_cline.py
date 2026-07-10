"""
NeuralCline Cline Adapter — Integration with Cline AI Coding Agent
====================================================================
Provides NeuralCline session safety for the Cline VS Code extension.

This adapter:
  1. Detects Cline installation paths
  2. Creates symlinks for hooks and rules
  3. Tunes shellIntegrationTimeout to 60s
  4. Installs .clinerules with rehydration directive
  5. Sets up auto-init hooks in .bashrc

Usage:
    from lib.adapters import get_adapter
    cline = get_adapter('cline')
    cline.install()
    print(cline.detect())
"""

import os
import sys
import json
import shutil
from pathlib import Path

from lib.adapters.base import BaseAdapter


class ClineAdapter(BaseAdapter):
    """Adapter for Cline AI coding agent (VS Code extension)."""
    
    @property
    def name(self):
        return 'Cline'
    
    @property
    def agent_id(self):
        return 'cline'
    
    def __init__(self):
        self.nc_dir = os.environ.get('NEURALCLINE_HOME', '/root/NeuralCline')
        self.session_dir = os.environ.get(
            'NEURALCLINE_SESSION_DIR',
            os.path.join(self.nc_dir, 'session-state')
        )
        self.cline_dir = '/root/Cline'
        self.cline_hooks = os.path.join(self.cline_dir, 'Hooks')
        self.cline_rules = os.path.join(self.cline_dir, 'Rules')
        self.clinerules_file = '/root/.clinerules'
        self.bashrc_file = '/root/.bashrc'
        self.rehydration_file = '/root/rehydration.md'
        self.master_profile = '/root/master_profile.md'
        self.autoinit_file = os.path.join(self.session_dir, 'auto-init.sh')
    
    def detect(self):
        """
        Detect if Cline is installed and return installation details.
        
        Checks for:
        1. Cline directory at /root/Cline/
        2. Cline globalState.json
        3. .clinerules file
        4. VS Code extensions directory
        """
        result = {
            'present': False,
            'path': None,
            'version': None,
            'config': None,
            'details': []
        }
        
        # Check 1: Cline directory
        if os.path.exists(self.cline_dir):
            result['path'] = self.cline_dir
            result['details'].append('cline_dir_found')
            
            # Check for hooks/rules subdirectories
            if os.path.exists(self.cline_hooks):
                result['details'].append('hooks_dir_found')
            if os.path.exists(self.cline_rules):
                result['details'].append('rules_dir_found')
        
        # Check 2: Cline globalState.json
        state_file = self._find_global_state()
        if state_file:
            result['config'] = state_file
            result['details'].append('global_state_found')
            
            # Try to read version
            try:
                with open(state_file) as f:
                    config = json.load(f)
                if isinstance(config, dict):
                    timeout = config.get('shellIntegrationTimeout', 'not_set')
                    result['details'].append(f'timeout={timeout}ms')
            except Exception:
                pass
        
        # Check 3: .clinerules
        if os.path.exists(self.clinerules_file):
            result['details'].append('clinerules_found')
        
        # Check 4: VS Code extensions
        vscode_extensions = [
            '/root/.vscode-server/extensions',
            '/root/.local/share/code-server/extensions',
            '/root/.config/Code/extensions',
        ]
        for ext_dir in vscode_extensions:
            if os.path.exists(ext_dir):
                for item in os.listdir(ext_dir):
                    if 'claude' in item.lower() or 'cline' in item.lower():
                        result['details'].append(f'extension_found:{item}')
                        result['present'] = True
                        break
        
        # Try to get version from extension manifest
        if result['present']:
            result['version'] = self.get_version()
        
        return result
    
    def get_version(self):
        """Get Cline extension version from VS Code extension manifest."""
        vscode_extensions = [
            '/root/.vscode-server/extensions',
            '/root/.local/share/code-server/extensions',
            '/root/.config/Code/extensions',
        ]
        
        for ext_dir in vscode_extensions:
            if not os.path.exists(ext_dir):
                continue
            for item in os.listdir(ext_dir):
                if 'claude' in item.lower() or 'cline' in item.lower():
                    manifest_path = os.path.join(ext_dir, item, 'package.json')
                    if os.path.exists(manifest_path):
                        try:
                            with open(manifest_path) as f:
                                manifest = json.load(f)
                            return manifest.get('version', 'unknown')
                        except Exception:
                            pass
        return 'unknown'
    
    def get_config_path(self):
        """Get Cline configuration file paths."""
        candidates = [
            "/root/.local/share/code-server/User/globalStorage/saoudrizwan.claude-dev/globalState.json",
            "/root/.config/Code/User/globalStorage/saoudrizwan.claude-dev/globalState.json",
            "/root/.vscode-server/data/User/globalStorage/saoudrizwan.claude-dev/globalState.json",
            "/root/.config/Code - OSS/User/globalStorage/saoudrizwan.claude-dev/globalState.json",
        ]
        found = []
        for c in candidates:
            if os.path.exists(c):
                found.append(c)
        return found
    
    def install(self):
        """
        Install NeuralCline integration for Cline.
        
        Steps:
        1. Create Cline hooks and rules directories
        2. Create symlinks for hooks
        3. Create symlinks for rules
        4. Install rehydration.md at /root/rehydration.md
        5. Install master_profile.md at /root/master_profile.md
        6. Install .clinerules
        7. Install auto-init.sh
        8. Add auto-init hook to .bashrc
        9. Tune Cline globalState.json
        """
        results = []
        
        # Step 1: Create directories
        os.makedirs(self.cline_hooks, exist_ok=True)
        os.makedirs(self.cline_rules, exist_ok=True)
        results.append({'step': 'create_dirs', 'status': 'ok'})
        
        # Step 2: Create hook symlinks
        hooks = ['pre-tool-guard.sh', 'post-tool-state.sh', 'generate-handoff.sh', 'diagnose.sh']
        for hook in hooks:
            src = os.path.join(self.nc_dir, 'hooks', hook)
            dst = os.path.join(self.cline_hooks, hook)
            if os.path.exists(src):
                # Remove old symlink if it exists
                if os.path.islink(dst) or os.path.exists(dst):
                    os.unlink(dst)
                os.symlink(src, dst)
                results.append({'step': f'symlink_hook:{hook}', 'status': 'ok'})
            else:
                results.append({'step': f'symlink_hook:{hook}', 'status': 'skipped', 'reason': f'{src} not found'})
        
        # Step 3: Create rule symlinks
        rules = ['session-safety.md', 'recovery-protocols.md']
        for rule in rules:
            src = os.path.join(self.nc_dir, 'rules', rule)
            dst = os.path.join(self.cline_rules, rule)
            if os.path.exists(src):
                if os.path.islink(dst) or os.path.exists(dst):
                    os.unlink(dst)
                os.symlink(src, dst)
                results.append({'step': f'symlink_rule:{rule}', 'status': 'ok'})
            else:
                results.append({'step': f'symlink_rule:{rule}', 'status': 'skipped', 'reason': f'{src} not found'})
        
        # Step 4: Install rehydration.md
        rehydration_src = os.path.join(self.nc_dir, 'rehydration.md')
        if os.path.exists(rehydration_src):
            shutil.copy2(rehydration_src, self.rehydration_file)
            os.chmod(self.rehydration_file, 0o755)
            results.append({'step': 'install_rehydration', 'status': 'ok'})
        
        # Step 5: Install master_profile.md
        profile_src = os.path.join(self.nc_dir, 'master_profile.md')
        if os.path.exists(profile_src):
            shutil.copy2(profile_src, self.master_profile)
            os.chmod(self.master_profile, 0o644)
            results.append({'step': 'install_master_profile', 'status': 'ok'})
        
        # Step 6: Install .clinerules
        self._install_clinerules()
        results.append({'step': 'install_clinerules', 'status': 'ok'})
        
        # Step 7: Install auto-init.sh
        self._install_auto_init()
        results.append({'step': 'install_auto_init', 'status': 'ok'})
        
        # Step 8: Add to .bashrc
        bashrc_result = self._install_bashrc_hook()
        results.append(bashrc_result)
        
        # Step 9: Tune Cline configuration
        tune_result = self._tune_cline_config()
        results.append(tune_result)
        
        # Step 10: Generate initial checkpoint
        try:
            from lib.session_core import SessionCore
            core = SessionCore()
            core.generate_checkpoint()
            results.append({'step': 'generate_checkpoint', 'status': 'ok'})
        except Exception as e:
            results.append({'step': 'generate_checkpoint', 'status': 'error', 'reason': str(e)})
        
        return {
            'adapter': 'cline',
            'installed': True,
            'steps': results,
            'errors': [r for r in results if r.get('status') == 'error']
        }
    
    def uninstall(self):
        """Remove NeuralCline integration for Cline."""
        results = []
        
        # Remove hook symlinks
        hooks = ['pre-tool-guard.sh', 'post-tool-state.sh', 'generate-handoff.sh', 'diagnose.sh']
        for hook in hooks:
            dst = os.path.join(self.cline_hooks, hook)
            if os.path.islink(dst):
                os.unlink(dst)
                results.append({'step': f'remove_symlink:{hook}', 'status': 'ok'})
        
        # Remove rule symlinks
        rules = ['session-safety.md', 'recovery-protocols.md']
        for rule in rules:
            dst = os.path.join(self.cline_rules, rule)
            if os.path.islink(dst):
                os.unlink(dst)
                results.append({'step': f'remove_symlink:{rule}', 'status': 'ok'})
        
        # Remove .clinerules (backup first)
        if os.path.exists(self.clinerules_file):
            backup = self.clinerules_file + '.backup'
            shutil.copy2(self.clinerules_file, backup)
            os.unlink(self.clinerules_file)
            results.append({'step': 'remove_clinerules', 'status': 'ok', 'backup': backup})
        
        # Remove bashrc hook
        if os.path.exists(self.bashrc_file):
            with open(self.bashrc_file) as f:
                lines = f.readlines()
            lines = [l for l in lines if 'auto-init.sh' not in l and 'NeuralCline' not in l]
            with open(self.bashrc_file, 'w') as f:
                f.writelines(lines)
            results.append({'step': 'remove_bashrc_hook', 'status': 'ok'})
        
        return {
            'adapter': 'cline',
            'uninstalled': True,
            'steps': results
        }
    
    def _check_installation(self):
        """Check if NeuralCline is installed for Cline."""
        checks = []
        
        # Check hook symlinks
        for hook in ['pre-tool-guard.sh', 'post-tool-state.sh', 'generate-handoff.sh']:
            dst = os.path.join(self.cline_hooks, hook)
            checks.append(os.path.islink(dst) and os.path.exists(dst))
        
        # Check .clinerules
        checks.append(os.path.exists(self.clinerules_file))
        
        # Check rehydration
        checks.append(os.path.exists(self.rehydration_file))
        
        # Check bashrc
        if os.path.exists(self.bashrc_file):
            with open(self.bashrc_file) as f:
                content = f.read()
            checks.append('auto-init.sh' in content)
        else:
            checks.append(False)
        
        return all(checks) if checks else False
    
    def _find_global_state(self):
        """Find Cline's globalState.json."""
        candidates = [
            "/root/.local/share/code-server/User/globalStorage/saoudrizwan.claude-dev/globalState.json",
            "/root/.config/Code/User/globalStorage/saoudrizwan.claude-dev/globalState.json",
            "/root/.vscode-server/data/User/globalStorage/saoudrizwan.claude-dev/globalState.json",
            "/root/.config/Code - OSS/User/globalStorage/saoudrizwan.claude-dev/globalState.json",
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None
    
    def _install_clinerules(self):
        """Install .clinerules file."""
        clinerules_content = """# =============================================================================
# NEURALCLINE — Neural Session Safety System (v2.0.0)
# =============================================================================
# Codename: EDGECASE
# Workspace: /root/NeuralCline/
#
# These rules are loaded automatically by Cline for every session.
# ⚠️ CRITICAL: The FIRST instruction below must be executed immediately.

## 🚨 MANDATORY FIRST ACTION
Run as your very first action in EVERY new session:
source /root/rehydration.md

This restores context from the last checkpoint so you can continue seamlessly.
After running it, read /root/master_profile.md for workspace context.

## SESSION CONTINUITY
Every tool call should use NeuralCline's session core for state management.
If context > 60%, truncate/paginate output and save checkpoint.
If context > 80%, save checkpoint before every tool call.
Every 50 tool calls, generate a handoff automatically.

## CRASH RECOVERY
Protocol A (session hang): source /root/rehydration.md
Protocol B (context full): bash hooks/generate-handoff.sh
Protocol C (output fail): tail -5 session-state/crash-log.ndjson
Protocol D (crash): source /root/rehydration.md
Protocol E (infinite loop): bash hooks/generate-handoff.sh
Protocol F (big file): ls -lh <file> then head -100 <file>
Protocol G (diagnose): bash hooks/diagnose.sh

## CRASH-FREE PYTHON EXECUTION
NEVER use inline `python3 -c "..."` — use file-based Python instead.
All session state operations must route through session_core.py.

## TERMINAL SAFETY
shellIntegrationTimeout is 60s (tuned up from 10s).
For commands expected > 30s: use `timeout 60s` wrapper.
For output > 500 lines: pipe through `head -200` or `grep`.
If output capture fails: check crash-log.ndjson, re-run with `head`.
Redirect stderr to stdout: `2>&1`.
"""
        with open(self.clinerules_file, 'w') as f:
            f.write(clinerules_content)
        os.chmod(self.clinerules_file, 0o644)
    
    def _install_auto_init(self):
        """Install auto-init.sh for shell-level session recovery."""
        autoinit_content = """#!/bin/bash
# =============================================================================
# 🚀 AUTO-INIT — Shell-Level Session Recovery Hook (v2.0.0)
# =============================================================================
# Source this from .bashrc to auto-restore session context every time
# a new terminal is opened.

if [[ $- != *i* ]]; then
    return
fi

SESSION_DIR="/root/.session-state"
CHECKPOINT="$SESSION_DIR/checkpoint.json"

if [ -f "$CHECKPOINT" ]; then
    python3 /root/NeuralCline/lib/session_core.py check-checkpoint 2>/dev/null || \
    echo "[Neural Safety] Run: source /root/rehydration.md"
fi
"""
        with open(self.autoinit_file, 'w') as f:
            f.write(autoinit_content)
        os.chmod(self.autoinit_file, 0o755)
    
    def _install_bashrc_hook(self):
        """Add auto-init hook to .bashrc."""
        if not os.path.exists(self.bashrc_file):
            return {'step': 'install_bashrc_hook', 'status': 'skipped', 'reason': '.bashrc not found'}
        
        with open(self.bashrc_file) as f:
            content = f.read()
        
        if 'auto-init.sh' in content:
            return {'step': 'install_bashrc_hook', 'status': 'skipped', 'reason': 'already installed'}
        
        with open(self.bashrc_file, 'a') as f:
            f.write('\n# NeuralCline — auto-restore session context on terminal open\n')
            f.write(f'if [ -f {self.autoinit_file} ]; then source {self.autoinit_file}; fi\n')
        
        return {'step': 'install_bashrc_hook', 'status': 'ok'}
    
    def _tune_cline_config(self):
        """Tune Cline's globalState.json settings."""
        state_file = self._find_global_state()
        if not state_file:
            return {'step': 'tune_config', 'status': 'skipped', 'reason': 'globalState.json not found'}
        
        try:
            with open(state_file) as f:
                config = json.load(f)
            
            if not isinstance(config, dict):
                return {'step': 'tune_config', 'status': 'error', 'reason': 'config is not a dict'}
            
            # Backup
            backup = state_file + '.backup'
            with open(backup, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Tune settings
            changes = {}
            if config.get('shellIntegrationTimeout') != 60000:
                changes['shellIntegrationTimeout'] = f"{config.get('shellIntegrationTimeout', 'not_set')}ms -> 60000ms"
                config['shellIntegrationTimeout'] = 60000
            
            if config.get('terminalOutputLineLimit') != 3000:
                changes['terminalOutputLineLimit'] = f"{config.get('terminalOutputLineLimit', 'not_set')} -> 3000"
                config['terminalOutputLineLimit'] = 3000
            
            if changes:
                with open(state_file, 'w') as f:
                    json.dump(config, f, indent=2)
                return {'step': 'tune_config', 'status': 'ok', 'changes': changes}
            else:
                return {'step': 'tune_config', 'status': 'ok', 'changes': 'already tuned'}
        
        except Exception as e:
            return {'step': 'tune_config', 'status': 'error', 'reason': str(e)}