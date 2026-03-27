#!/usr/bin/env node
// Block modifications to .env files and migration files
// Exit 0 = allow, Exit 2 = block

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => { input += chunk; });
process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input);
    const filePath = data?.tool_input?.file_path || '';

    if (!filePath) {
      process.exit(0);
    }

    // Block .env files
    const basename = filePath.split('/').pop().split('\\').pop();
    if (basename === '.env' || basename.startsWith('.env.')) {
      process.stderr.write('BLOCKED: Do not modify .env files directly\n');
      process.exit(2);
    }

    // Block migration files
    const normalizedPath = filePath.replace(/\\/g, '/');
    if (normalizedPath.includes('prisma/migrations/') || normalizedPath.includes('alembic/versions/')) {
      process.stderr.write('BLOCKED: Do not modify migration files directly\n');
      process.exit(2);
    }
    process.exit(0);
  } catch {
    process.exit(0);
  }
});
