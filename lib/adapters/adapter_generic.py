"""
NeuralCline Generic Adapter — Any Shell-Based AI Agent
========================================================
Provides NeuralCline session safety for any shell-based AI coding agent
that doesn't have a specific adapter. This is the fallback adapter.

Works with:
  - Any agent that uses bash/zsh/fish for command execution
  - Any agent that can source shell hooks from .bashrc
  - Any VS Code extension that uses the integrated terminal

Usage:
    from lib.adapters import get_adapter
    generic = get_adapter('generic')
    generic.install()
    print(generic.detect())
"""

import os
import sys
import json
from pathlib import Path

from lib.adapters.base import BaseAdapter


class GenericAdapter(BaseAdapter):
    """Generic adapter for any shell-based AI agent."""
    
    @property
    def name(self):
        return 'Generic Shell Agent'
    
    @property
    def agent_id(self):
        return 'generic'
    
    def __init__(self):
        self.nc_dir = os.environ.get('NEURALCLINE_HOME', '/root/NeuralCline')
        self.session_dir = os.environ.get(
            'NEURALCLINE_SESSION_DIR',
            os.path.join(self.nc_dir, 'session-state')
        )
        self.bashrc_file = '/root/.bashrc'
        self.bash_profile = '/root/.bash_profile'
        self.zshrc_file = '/root/.zshrc'
        self.autoinit_file = os.path.join(self.session_dir, 'auto-init.sh')
        self.shell_hooks_file = os.path.join(self.nc_dir, 'hooks', 'shell-hooks.sh')
    
    def detect(self):
        """
        Detect if this environment supports generic shell integration.
        
        Checks for:
        1. Shell configuration files (.bashrc, .zshrc)
        2. Whether we can source shell hooks
        3. Current shell type
        """
        result = {
            'present': False,
            'shell': os.environ.get('SHELL', 'unknown'),
            'config_files': [],
            'details': []
        }
        
        # Check shell config files
        configs = [
            ('bashrc', self.bashrc_file),
            ('bash_profile', self.bash_profile),
            ('zshrc', self.zshrc_file),
        ]
        for name, path in configs:
            if os.path.exists(path):
                result['config_files'].append(path)
                result['details'].append(f'{name}_found')
        
        # Check if shell hooks exist
        if os.path.exists(self.shell_hooks_file):
            result['details'].append('shell_hooks_available')
        
        # Check if we can write to shell config
        for path in [self.bashrc_file, self.zshrc_file]:
            if os.path.exists(path) and os.access(path, os.W_OK):
                result['present'] = True
                result['details'].append('config_writable')
                break
            elif not os.path.exists(path):
                # Can create new config file
                result['present'] = True
                result['details'].append('can_create_config')
                break
        
        return result
    
    def get_version(self):
        """Get shell version."""
        return os.environ.get('SHELL', 'unknown')
    
    def get_config_path(self):
        """Get shell configuration file paths."""
        paths = []
        for p in [self.bashrc_file, self.bash_profile, self.zshrc_file]:
            if os.path.exists(p):
                paths.append(p)
        return paths if paths else [self.bashrc_file]
    
    def install(self):
        """
        Install NeuralCline integration for generic shell agent.
        
        Steps:
        1. Install shell hooks (DEBUG trap + PROMPT_COMMAND)
        2. Add auto-init to shell config
        3. Install .clinerules (if applicable)
        4. Generate initial checkpoint
        """
        results = []
        
        # Step 1: Install shell hooks
        if os.path.exists(self.shell_hooks_file):
            self._install_shell_hooks()
            results.append({'step': 'install_shell_hooks', 'status': 'ok'})
        else:
            results.append({'step': 'install_shell_hooks', 'status': 'skipped', 'reason': 'shell-hooks.sh not found'})
        
        # Step 2: Add auto-init to shell config
        for config_file in [self.bashrc_file, self.zshrc_file]:
            result = self._install_auto_init(config_file)
            if result['status'] != 'skipped':
                results.append(result)
        
        if not any(r.get('step', '').startswith('install_auto_init') for r in results if r.get('status') == 'ok'):
            # Fallback to .bashrc
            result = self._install_auto_init(self.bashrc_file)
            results.append(result)
        
        # Step 3: Generate checkpoint
        try:
            from lib.session_core import SessionCore
            core = SessionCore()
            core.generate_checkpoint()
            results.append({'step': 'generate_checkpoint', 'status': 'ok'})
        except Exception as e:
            results.append({'step': 'generate_checkpoint', 'status': 'error', 'reason': str(e)})
        
        return {
            'adapter': 'generic',
            'installed': True,
            'steps': results,
            'errors': [r for r in results if r.get('status') == 'error']
        }
    
    def uninstall(self):
        """
        Remove NeuralCline integration for generic shell agent.
        
        Steps:
        1. Remove shell hooks from config files
        2. Remove auto-init references
        """
        results = []
        
        for config_file in [self.bashrc_file, self.bash_profile, self.zshrc_file]:
            if os.path.exists(config_file):
                with open(config_file) as f:
                    lines = f.readlines()
                original_count = len(lines)
                lines = [l for l in lines if 'auto-init.sh' not in l and 'NeuralCline' not in l and 'shell-hooks.sh' not in l]
                if len(lines) != original_count:
                    with open(config_file, 'w') as f:
                        f.writelines(lines)
                    results.append({'step': f'clean_config:{config_file}', 'status': 'ok'})
        
        if not results:
            results.append({'step': 'clean_config', 'status': 'skipped', 'reason': 'no config files modified'})
        
        return {
            'adapter': 'generic',
            'uninstalled': True,
            'steps': results
        }
    
    def _check_installation(self):
        """Check if NeuralCline is installed for generic shell."""
        checks = []
        
        # Check shell config files
        for config_file in [self.bashrc_file, self.zshrc_file]:
            if os.path.exists(config_file):
                with open(config_file) as f:
                    content = f.read()
                checks.append('auto-init.sh' in content or 'NeuralCline' in content)
        
        # Check shell hooks
        checks.append(os.path.exists(self.shell_hooks_file))
        
        return any(checks)
    
    def _install_shell_hooks(self):
        """Install shell hooks by adding to .bashrc."""
        hook_line = f'\n# NeuralCline — shell hooks for automatic hang/crash detection\n[ -f {self.shell_hooks_file} ] && source {self.shell_hooks_file}\n'
        
        for config_file in [self.bashrc_file, self.zshrc_file]:
            if os.path.exists(config_file):
                with open(config_file) as f:
                    content = f.read()
                if 'shell-hooks.sh' not in content:
                    with open(config_file, 'a') as f:
                        f.write(hook_line)
    
    def _install_auto_init(self, config_file):
        """Add auto-init hook to a shell config file."""
        if not os.path.exists(config_file):
            # Create the file
            with open(config_file, 'w') as f:
                f.write('#!/bin/bash\n')
        
        with open(config_file) as f:
            content = f.read()
        
        if 'auto-init.sh' in content:
            return {'step': f'install_auto_init:{config_file}', 'status': 'skipped', 'reason': 'already installed'}
        
        with open(config_file, 'a') as f:
            f.write('\n# NeuralCline — auto-restore session context on terminal open\n')
            f.write(f'if [ -f {self.autoinit_file} ]; then source {self.autoinit_file}; fi\n')
        
        return {'step': f'install_auto_init:{config_file}', 'status': 'ok'}