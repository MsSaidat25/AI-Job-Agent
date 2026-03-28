#!/usr/bin/env node

/**
 * ChainProof MCP Server — local file-based trust chain operations.
 *
 * Provides tools for recording AI decisions, tracking code provenance,
 * and verifying trust chain integrity. Runs over stdio, no dependencies
 * beyond Node.js built-ins.
 *
 * Auto-configured by DevForge. No setup required.
 */

import fs from 'node:fs';
import path from 'node:path';
import { createHash, generateKeyPairSync, sign, verify, randomUUID } from 'node:crypto';
import { createInterface } from 'node:readline';

// --- Project directory resolution ---

const PROJECT_DIR = process.env.CHAINPROOF_PROJECT_DIR || process.cwd();
const CP_DIR = path.join(PROJECT_DIR, '.chainproof');
const GENESIS_HASH = '0'.repeat(64);

// --- Crypto primitives ---

function hashContent(content) {
  return createHash('sha256').update(content, 'utf-8').digest('hex');
}

function signEntry(content, privateKeyPem) {
  const signature = sign(null, Buffer.from(content, 'utf-8'), privateKeyPem);
  return signature.toString('base64');
}

function verifySignature(content, signatureB64, publicKeyPem) {
  try {
    return verify(null, Buffer.from(content, 'utf-8'), publicKeyPem, Buffer.from(signatureB64, 'base64'));
  } catch {
    return false;
  }
}

function computeChainHash(prevHash, contentHash) {
  return createHash('sha256').update(prevHash + contentHash, 'utf-8').digest('hex');
}

// --- File operations ---

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
}

function writeJson(filePath, data) {
  const tmp = filePath + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(data, null, 2) + '\n', 'utf-8');
  fs.renameSync(tmp, filePath);
}

function ensureInitialized() {
  if (!fs.existsSync(CP_DIR)) {
    throw new Error(
      'No .chainproof/ directory found. Run "devforge init" or "chainproof init" first.'
    );
  }
}

// --- Tool implementations ---

function recordDecision(content, entryType = 'decision') {
  ensureInitialized();
  const chainPath = path.join(CP_DIR, 'chain.json');
  const chain = readJson(chainPath);

  const contentHash = hashContent(content);
  const prevHash = chain.currentHash;
  const chainHash = computeChainHash(prevHash, contentHash);

  let signature = null;
  const keyPath = path.join(CP_DIR, 'keys', 'private.pem');
  if (fs.existsSync(keyPath)) {
    signature = signEntry(content, fs.readFileSync(keyPath, 'utf-8'));
  }

  const entry = {
    id: randomUUID(),
    timestamp: new Date().toISOString(),
    entryType,
    content,
    contentHash,
    prevHash,
    chainHash,
    signature,
    sessionId: 'mcp-server',
  };

  chain.entries.push(entry);
  chain.currentHash = chainHash;
  writeJson(chainPath, chain);

  return { id: entry.id, chainHash, signed: signature !== null };
}

function recordCode(filePath, contentHash, generator = 'unknown', language = null) {
  ensureInitialized();
  const artifactsPath = path.join(CP_DIR, 'artifacts.json');
  const data = readJson(artifactsPath);

  const record = {
    id: randomUUID(),
    timestamp: new Date().toISOString(),
    filePath,
    contentHash,
    language,
    generator,
    promptHash: null,
    nllEntryId: null,
  };

  data.artifacts.push(record);
  writeJson(artifactsPath, data);

  return { id: record.id, filePath: record.filePath };
}

function verifyChainIntegrity() {
  ensureInitialized();
  const chain = readJson(path.join(CP_DIR, 'chain.json'));
  const errors = [];
  let expectedHash = GENESIS_HASH;

  for (let i = 0; i < chain.entries.length; i++) {
    const entry = chain.entries[i];

    if (entry.prevHash !== expectedHash) {
      errors.push(`Entry ${i}: prevHash mismatch`);
    }
    if (entry.contentHash !== hashContent(entry.content)) {
      errors.push(`Entry ${i}: content was tampered`);
    }
    if (entry.chainHash !== computeChainHash(entry.prevHash, entry.contentHash)) {
      errors.push(`Entry ${i}: chainHash mismatch`);
    }
    if (entry.signature) {
      const pubPath = path.join(CP_DIR, 'keys', 'public.pem');
      if (fs.existsSync(pubPath)) {
        if (!verifySignature(entry.content, entry.signature, fs.readFileSync(pubPath, 'utf-8'))) {
          errors.push(`Entry ${i}: invalid signature`);
        }
      }
    }
    expectedHash = entry.chainHash;
  }

  if (chain.entries.length > 0 && chain.currentHash !== expectedHash) {
    errors.push('currentHash does not match last entry');
  }

  return { valid: errors.length === 0, errors, entryCount: chain.entries.length };
}

function getStatus() {
  ensureInitialized();
  const chain = readJson(path.join(CP_DIR, 'chain.json'));

  let config = {};
  const configPath = path.join(CP_DIR, 'config.json');
  if (fs.existsSync(configPath)) config = readJson(configPath);

  let artifacts = { artifacts: [] };
  const artPath = path.join(CP_DIR, 'artifacts.json');
  if (fs.existsSync(artPath)) artifacts = readJson(artPath);

  const unsigned = chain.entries.filter(e => !e.signature).length;

  return {
    initialized: true,
    projectName: config.projectName || path.basename(PROJECT_DIR),
    entryCount: chain.entries.length,
    artifactCount: artifacts.artifacts.length,
    currentHash: chain.currentHash,
    unsignedEntries: unsigned,
    createdAt: config.createdAt || null,
    lastEntry: chain.entries.length > 0 ? chain.entries[chain.entries.length - 1].timestamp : null,
  };
}

// --- MCP Protocol (JSON-RPC over stdio) ---

const TOOLS = [
  {
    name: 'chainproof_record_decision',
    description: 'Record an AI decision in the trust chain. Use this when making architectural decisions, choosing implementations, or any significant choice during development.',
    inputSchema: {
      type: 'object',
      properties: {
        content: { type: 'string', description: 'The decision content to record' },
        entry_type: { type: 'string', description: 'Type of entry: decision, implementation, review, refactor', default: 'decision' },
      },
      required: ['content'],
    },
  },
  {
    name: 'chainproof_record_code',
    description: 'Record code provenance. Track who or what generated a file and its content hash.',
    inputSchema: {
      type: 'object',
      properties: {
        file_path: { type: 'string', description: 'Relative path to the file' },
        content_hash: { type: 'string', description: 'SHA-256 hash of the file content' },
        generator: { type: 'string', description: 'What generated this code (e.g., "claude-opus-4-6", "human")', default: 'unknown' },
        language: { type: 'string', description: 'Programming language' },
      },
      required: ['file_path', 'content_hash'],
    },
  },
  {
    name: 'chainproof_verify',
    description: 'Verify the integrity of the trust chain. Checks hash linking, content hashes, and signatures.',
    inputSchema: { type: 'object', properties: {} },
  },
  {
    name: 'chainproof_status',
    description: 'Get the current status of the trust chain: entry count, artifact count, signature status.',
    inputSchema: { type: 'object', properties: {} },
  },
];

function handleToolCall(name, args) {
  try {
    switch (name) {
      case 'chainproof_record_decision':
        return recordDecision(args.content, args.entry_type || 'decision');
      case 'chainproof_record_code':
        return recordCode(args.file_path, args.content_hash, args.generator, args.language);
      case 'chainproof_verify':
        return verifyChainIntegrity();
      case 'chainproof_status':
        return getStatus();
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (err) {
    return { error: err.message };
  }
}

function handleRequest(request) {
  const { method, params, id } = request;

  switch (method) {
    case 'initialize':
      return {
        jsonrpc: '2.0',
        id,
        result: {
          protocolVersion: '2024-11-05',
          capabilities: { tools: {} },
          serverInfo: { name: 'chainproof', version: '1.0.0' },
        },
      };

    case 'notifications/initialized':
      return null; // no response for notifications

    case 'tools/list':
      return { jsonrpc: '2.0', id, result: { tools: TOOLS } };

    case 'tools/call': {
      const result = handleToolCall(params.name, params.arguments || {});
      const isError = result && result.error;
      return {
        jsonrpc: '2.0',
        id,
        result: {
          content: [{ type: 'text', text: JSON.stringify(result, null, 2) }],
          isError: !!isError,
        },
      };
    }

    default:
      return {
        jsonrpc: '2.0',
        id,
        error: { code: -32601, message: `Method not found: ${method}` },
      };
  }
}

// --- stdio transport ---

const rl = createInterface({ input: process.stdin, terminal: false });
let buffer = '';

process.stdin.setEncoding('utf-8');

rl.on('line', (line) => {
  try {
    const request = JSON.parse(line);
    const response = handleRequest(request);
    if (response) {
      process.stdout.write(JSON.stringify(response) + '\n');
    }
  } catch {
    // Skip malformed JSON
  }
});

process.on('SIGINT', () => process.exit(0));
process.on('SIGTERM', () => process.exit(0));
