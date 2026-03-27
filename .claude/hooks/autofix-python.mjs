#!/usr/bin/env node
// Auto-fix lint issues on saved Python files

import { execFileSync } from 'node:child_process';
import { resolve, sep } from 'node:path';

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => { input += chunk; });
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input);
    const filePath = data?.tool_input?.file_path || '';

    if (!filePath || filePath.includes('..')) {
      process.exit(0);
    }

    // Ensure path stays within the working directory
    const resolved = resolve(filePath);
    const cwd = resolve('.');
    if (!resolved.startsWith(cwd + sep) && resolved !== cwd) {
      process.exit(0);
    }

    if (filePath.endsWith('.py')) {
      try {
        execFileSync('ruff', ['check', '--fix', resolved], { stdio: 'pipe' });
      } catch {
        // ruff may exit non-zero for unfixable issues — that's okay
      }
    }
    process.exit(0);
  } catch {
    process.exit(0);
  }
});
