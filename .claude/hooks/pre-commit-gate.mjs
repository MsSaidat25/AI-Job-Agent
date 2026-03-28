#!/usr/bin/env node

/**
 * Pre-commit gate — the single quality checkpoint before any commit.
 * Replaces /done. Triggered by PreToolUse hook on Bash when command contains "git commit".
 *
 * Phase 1 (automated, fast):
 *   - No .env files or secrets staged
 *   - No merge conflict markers
 *   - Lint passes
 *   - Tests pass
 *
 * Phase 2 (agent review):
 *   - Tells Claude to run code-quality-reviewer and security-reviewer on changed files
 *   - Only triggers if Phase 1 passes and changed files haven't been reviewed yet
 *
 * Exit 0 = allow commit
 * Exit 2 = block commit with message
 */

import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const input = process.env.CLAUDE_TOOL_INPUT || '{}';

let parsed;
try {
  parsed = JSON.parse(input);
} catch {
  process.exit(0);
}

const command = parsed.command || '';

// Only gate actual git commit commands
if (!command.match(/git\s+commit/)) {
  process.exit(0);
}

// Skip amend-only or empty commits
if (command.includes('--allow-empty')) {
  process.exit(0);
}

const errors = [];

// Get staged files once, reuse across checks
let stagedFiles = '';
try {
  stagedFiles = execSync('git diff --cached --name-only', { encoding: 'utf-8' }).trim();
} catch {
  // git not available
}

// === PHASE 1: Automated checks ===

// Check 1: No secrets staged
if (stagedFiles) {
  const secretFilePatterns = ['.env', 'credentials', '.pem', '.key'];
  const secretNamePatterns = ['secret'];
  const flagged = stagedFiles.split('\n').filter(f => {
    const base = path.basename(f).toLowerCase();
    if (f.includes('.chainproof/keys/public.pem')) return false;
    // Always flag secret file extensions regardless of language
    if (secretFilePatterns.some(p => base.includes(p))) return true;
    return secretNamePatterns.some(p => base.includes(p));
  });
  if (flagged.length > 0) {
    errors.push(`Potential secrets staged: ${flagged.join(', ')}\nUnstage these files or confirm they are safe.`);
  }
}

// Check 2: No merge conflict markers
try {
  const staged = execSync('git diff --cached', { encoding: 'utf-8' });
  if (staged.includes('<<<<<<<') || staged.includes('>>>>>>>')) {
    errors.push('Merge conflict markers found in staged changes. Resolve conflicts first.');
  }
} catch {
  // skip
}

// Helper: run a shell command, push to errors on failure
function tryExec(cmd, label, timeout = 30000) {
  try {
    execSync(`${cmd} 2>&1`, { encoding: 'utf-8', timeout });
    return true;
  } catch (e) {
    if (e.status || e.killed) {
      const msg = e.killed ? 'Command timed out' : (e.stdout || e.message);
      errors.push(`${label}:\n${String(msg).slice(0, 500)}`);
    }
    return false;
  }
}

function readPkg(file = 'package.json') {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf-8'));
  } catch {
    return null;
  }
}

// Check 3: Lint
function runLint() {
  if (fs.existsSync('package.json')) {
    const pkg = readPkg();
    if (!pkg) { errors.push('Lint skipped: package.json is malformed JSON'); return; }
    if (pkg.scripts?.lint) { tryExec('npm run lint', 'Lint failed'); return; }
    tryExec('npx eslint . --ext .js,.ts,.tsx', 'Lint failed');
    return;
  }
  if (fs.existsSync('requirements.txt') || fs.existsSync('pyproject.toml')) {
    tryExec('ruff check .', 'Lint failed');
    return;
  }
  if (fs.existsSync('frontend/package.json')) {
    tryExec('cd frontend && npx eslint .', 'Frontend lint failed');
  }
  if (fs.existsSync('backend/requirements.txt')) {
    tryExec('cd backend && ruff check .', 'Backend lint failed');
  }
}

// Check 4: Tests
function runTests() {
  const testTimeout = 120000;
  if (fs.existsSync('package.json')) {
    const pkg = readPkg();
    if (!pkg) { errors.push('Tests skipped: package.json is malformed JSON'); return; }
    if (pkg.scripts?.test) { tryExec('npm test', 'Tests failed', testTimeout); return; }
    tryExec('npx vitest run', 'Tests failed', testTimeout);
    return;
  }
  if (fs.existsSync('requirements.txt') || fs.existsSync('pyproject.toml')) {
    tryExec('pytest', 'Tests failed', testTimeout);
    return;
  }
  if (fs.existsSync('frontend/package.json')) {
    tryExec('cd frontend && npx vitest run', 'Frontend tests failed', testTimeout);
  }
  if (fs.existsSync('backend/requirements.txt')) {
    tryExec('cd backend && pytest', 'Backend tests failed', testTimeout);
  }
}

runLint();
runTests();

if (errors.length > 0) {
  console.error('[pre-commit] BLOCKED - fix these issues first:\n');
  errors.forEach(e => console.error(`  ${e}\n`));
  console.error('Run /build-fix to auto-resolve lint and build errors.');
  process.exit(2);
}

// === PHASE 2: Agent review gate ===
// Check if changed files have been reviewed in this session.
// We use a marker file that gets created when agents complete review.

const reviewMarker = '.claude/.last-review';
let needsReview = false;

try {
  if (!stagedFiles) {
    // Nothing staged, allow
    process.exit(0);
  }

  const stagedList = stagedFiles.split('\n').filter(f =>
    f.endsWith('.js') || f.endsWith('.ts') || f.endsWith('.tsx') ||
    f.endsWith('.py') || f.endsWith('.jsx') || f.endsWith('.mjs')
  );

  if (stagedList.length === 0) {
    // No code files staged (just docs/config), skip review
    process.exit(0);
  }

  if (fs.existsSync(reviewMarker)) {
    try {
      const review = JSON.parse(fs.readFileSync(reviewMarker, 'utf-8'));
      const reviewedFiles = new Set(review.files || []);
      const unreviewed = stagedList.filter(f => !reviewedFiles.has(f));
      if (unreviewed.length > 0) {
        needsReview = true;
      }
    } catch {
      needsReview = true;
    }
  } else {
    needsReview = true;
  }
} catch {
  // Can't determine, allow
  process.exit(0);
}

if (needsReview) {
  console.error('[pre-commit] Code review required before commit.\n');
  console.error('Run code-quality-reviewer and security-reviewer agents on the changed files,');
  console.error('then retry the commit. Or run /code-review to do this automatically.\n');
  console.error('To mark files as reviewed, the agents will update .claude/.last-review.');
  process.exit(2);
}
