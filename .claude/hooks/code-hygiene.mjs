#!/usr/bin/env node
// Code Hygiene Gate — runs on Stop to enforce structural quality
// Checks: file length, duplicate code blocks, repeated functions, stale test files
// Exit 0 = pass (with warnings), Exit 2 = blocked (critical issues found)

import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { join, relative, extname, basename } from 'node:path';

// ── Config ──────────────────────────────────────────────────────────────────
const MAX_FILE_LINES = 300;
const MAX_FUNCTION_LINES = 50;
const MIN_DUPLICATE_LINES = 6;       // minimum consecutive matching lines to flag
const MAX_FILES_PER_DIR = 20;        // warn if a single directory has too many files
const SOURCE_EXTENSIONS = new Set(['.ts', '.tsx', '.js', '.jsx', '.py', '.go', '.rs']);
const IGNORE_DIRS = new Set(['node_modules', '.next', '__pycache__', '.git', 'dist', 'build', '.claude', 'coverage', '.venv', 'venv']);
const IGNORE_FILES = new Set(['package-lock.json', 'pnpm-lock.yaml', 'yarn.lock']);

// ── Helpers ─────────────────────────────────────────────────────────────────
function walk(dir, files = []) {
  let entries;
  try { entries = readdirSync(dir, { withFileTypes: true }); } catch { return files; }
  for (const entry of entries) {
    if (IGNORE_DIRS.has(entry.name)) continue;
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(full, files);
    } else if (SOURCE_EXTENSIONS.has(extname(entry.name)) && !IGNORE_FILES.has(entry.name)) {
      files.push(full);
    }
  }
  return files;
}

function readLines(filePath) {
  try { return readFileSync(filePath, 'utf-8').split('\n'); } catch { return []; }
}

// ── Checks ──────────────────────────────────────────────────────────────────

function checkFileLengths(files, cwd) {
  const warnings = [];
  for (const file of files) {
    const lines = readLines(file);
    if (lines.length > MAX_FILE_LINES) {
      warnings.push({
        level: lines.length > MAX_FILE_LINES * 2 ? 'critical' : 'warning',
        file: relative(cwd, file),
        message: `${lines.length} lines (limit: ${MAX_FILE_LINES}). Split into smaller, focused modules.`,
      });
    }
  }
  return warnings;
}

function checkFunctionLengths(files, cwd) {
  const warnings = [];
  // Match common function declarations across JS/TS/Python
  const fnPatterns = [
    /^(?:export\s+)?(?:async\s+)?function\s+(\w+)/,          // function foo()
    /^(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s*)?\(/,  // const foo = (
    /^(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[^=])\s*=>/,  // const foo = () =>
    /^\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{/,               // method() {
    /^(?:async\s+)?def\s+(\w+)/,                               // def foo (Python)
  ];

  for (const file of files) {
    const fileExt = extname(file);
    if (fileExt === '.py') continue;

    const lines = readLines(file);
    let currentFn = null;
    let fnStart = 0;
    let braceDepth = 0;
    let inFunction = false;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Check if this line starts a new function
      let newFnStarted = false;
      for (const pattern of fnPatterns) {
        const match = line.match(pattern);
        if (match) {
          // Close previous function if open
          if (inFunction && currentFn) {
            const len = i - fnStart;
            if (len > MAX_FUNCTION_LINES) {
              warnings.push({
                level: 'warning',
                file: relative(cwd, file),
                message: `Function "${currentFn}" is ${len} lines (limit: ${MAX_FUNCTION_LINES}) at line ${fnStart + 1}. Extract helper functions.`,
              });
            }
          }
          currentFn = match[1];
          fnStart = i;
          inFunction = true;
          braceDepth = 0;
          newFnStarted = true;
          break;
        }
      }

      // Skip brace tracking on the line that started a new function
      if (newFnStarted) continue;

      // Track brace depth for JS/TS
      if (inFunction) {
        for (const ch of line) {
          if (ch === '{') braceDepth++;
          if (ch === '}') braceDepth--;
        }
        if (braceDepth <= 0 && i > fnStart && line.trim()) {
          const len = i - fnStart + 1;
          if (len > MAX_FUNCTION_LINES) {
            warnings.push({
              level: 'warning',
              file: relative(cwd, file),
              message: `Function "${currentFn}" is ${len} lines (limit: ${MAX_FUNCTION_LINES}) at line ${fnStart + 1}. Extract helper functions.`,
            });
          }
          inFunction = false;
          currentFn = null;
        }
      }
    }
  }
  return warnings;
}

function checkDuplicateBlocks(files, cwd) {
  const warnings = [];
  // Build a map of normalized line sequences -> locations
  const blockMap = new Map();

  for (const file of files) {
    const lines = readLines(file).map(l => l.trim()).filter(l => l && !l.startsWith('//') && !l.startsWith('#') && !l.startsWith('*') && !l.startsWith('import') && !l.startsWith('from'));

    // Sliding window of MIN_DUPLICATE_LINES
    for (let i = 0; i <= lines.length - MIN_DUPLICATE_LINES; i++) {
      const block = lines.slice(i, i + MIN_DUPLICATE_LINES).join('\n');
      // Skip trivial blocks (mostly braces, returns, empty patterns)
      if (block.replace(/[{}\s();\n]/g, '').length < 30) continue;

      if (!blockMap.has(block)) {
        blockMap.set(block, []);
      }
      blockMap.get(block).push({ file: relative(cwd, file), line: i + 1 });
    }
  }

  // Report blocks found in multiple files
  const reported = new Set();
  for (const [block, locations] of blockMap) {
    const uniqueFiles = [...new Set(locations.map(l => l.file))];
    if (uniqueFiles.length < 2) continue;

    const key = uniqueFiles.sort().join('|');
    if (reported.has(key)) continue;
    reported.add(key);

    const preview = block.split('\n')[0].substring(0, 60);
    warnings.push({
      level: 'warning',
      file: uniqueFiles[0],
      message: `Duplicate code block found in ${uniqueFiles.length} files: "${preview}..." Also in: ${uniqueFiles.slice(1).join(', ')}. Extract to a shared utility.`,
    });

    // Limit duplicate reports to avoid noise
    if (warnings.length > 5) break;
  }

  return warnings;
}

function checkDirectoryBloat(cwd) {
  const warnings = [];

  function checkDir(dir) {
    let entries;
    try { entries = readdirSync(dir, { withFileTypes: true }); } catch { return; }

    const sourceFiles = entries.filter(e =>
      !e.isDirectory() && SOURCE_EXTENSIONS.has(extname(e.name)) && !IGNORE_FILES.has(e.name)
    );

    if (sourceFiles.length > MAX_FILES_PER_DIR) {
      warnings.push({
        level: 'warning',
        file: relative(cwd, dir) || '.',
        message: `Directory has ${sourceFiles.length} source files (limit: ${MAX_FILES_PER_DIR}). Consider grouping into subdirectories by feature or domain.`,
      });
    }

    for (const entry of entries) {
      if (entry.isDirectory() && !IGNORE_DIRS.has(entry.name)) {
        checkDir(join(dir, entry.name));
      }
    }
  }

  checkDir(cwd);
  return warnings;
}

function checkStaleTests(files, cwd) {
  const warnings = [];
  const sourceFiles = new Set(
    files
      .filter(f => !basename(f).includes('.test.') && !basename(f).includes('.spec.') && !f.includes('__tests__'))
      .map(f => basename(f).replace(extname(f), ''))
  );

  const testFiles = files.filter(f =>
    basename(f).includes('.test.') || basename(f).includes('.spec.') || f.includes('__tests__')
  );

  for (const testFile of testFiles) {
    const testBase = basename(testFile)
      .replace('.test', '')
      .replace('.spec', '')
      .replace(extname(testFile), '');

    // If the source file this test corresponds to doesn't exist, flag it
    if (testBase && !sourceFiles.has(testBase)) {
      const lines = readLines(testFile);
      // Check if the test file imports something that doesn't exist
      const imports = lines.filter(l => l.includes('import') && l.includes('from'));
      let hasDeadImport = false;
      for (const imp of imports) {
        const match = imp.match(/from\s+['"]([^'"]+)['"]/);
        if (match && match[1].startsWith('.')) {
          // Relative import - check if the file exists
          const importPath = join(testFile, '..', match[1]);
          const extensions = ['.ts', '.tsx', '.js', '.jsx', '.py', ''];
          const exists = extensions.some(ext => existsSync(importPath + ext) || existsSync(importPath));
          if (!exists) hasDeadImport = true;
        }
      }

      if (hasDeadImport) {
        warnings.push({
          level: 'warning',
          file: relative(cwd, testFile),
          message: `Test file may be stale — imports reference files that no longer exist. Review and delete if no longer needed.`,
        });
      }
    }
  }

  return warnings;
}

// ── Main ────────────────────────────────────────────────────────────────────

const cwd = process.cwd();
const files = walk(cwd);

const allWarnings = [
  ...checkFileLengths(files, cwd),
  ...checkFunctionLengths(files, cwd),
  ...checkDuplicateBlocks(files, cwd),
  ...checkDirectoryBloat(cwd),
  ...checkStaleTests(files, cwd),
];

const criticals = allWarnings.filter(w => w.level === 'critical');
const warnings = allWarnings.filter(w => w.level === 'warning');

if (allWarnings.length === 0) {
  process.stderr.write('\n[code-hygiene] All clean. No structural issues found.\n');
  process.exit(0);
}

process.stderr.write('\n[code-hygiene] Structural quality report:\n\n');

for (const w of criticals) {
  process.stderr.write(`  CRITICAL  ${w.file}\n    ${w.message}\n\n`);
}
for (const w of warnings) {
  process.stderr.write(`  WARNING   ${w.file}\n    ${w.message}\n\n`);
}

process.stderr.write(`  Summary: ${criticals.length} critical, ${warnings.length} warnings\n\n`);

if (criticals.length > 0) {
  process.stderr.write('[code-hygiene] BLOCKED: Fix critical issues before completing.\n');
  process.stderr.write('  Tip: Use /simplify to auto-refactor long files and extract shared utilities.\n');
  process.exit(2);
}

process.stderr.write('[code-hygiene] Passed with warnings. Consider running /simplify to clean up.\n');
process.exit(0);
