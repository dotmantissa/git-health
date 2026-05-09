import { createClient } from 'genlayer-js';
import { studionet } from 'genlayer-js/chains';
import { ExecutionResult, TransactionStatus } from 'genlayer-js/types';
import {
  CONTRACT_ADDRESS,
  ABI,
  TX_POLL_INTERVAL,
  TX_POLL_RETRIES
} from '../constants';

export function buildGenLayerClient(accountAddress) {
  return createClient({
    chain: studionet,
    account: accountAddress
  });
}

export async function analyzeRepo(accountAddress, repoUrl, onStatus) {
  const client = buildGenLayerClient(accountAddress);

  onStatus?.('Submitting transaction…');

  const txHash = await client.writeContract({
    address: CONTRACT_ADDRESS,
    abi: ABI,
    functionName: 'analyze_repo',
    args: [repoUrl],
    value: BigInt(0)
  });

  onStatus?.('Waiting for LLM consensus… (this takes 30–90 seconds)');

  const receipt = await client.waitForTransactionReceipt({
    hash: txHash,
    status: TransactionStatus.FINALIZED,
    retries: TX_POLL_RETRIES,
    interval: TX_POLL_INTERVAL,
    fullTransaction: true
  });

  if (!receipt) {
    throw new Error('Transaction did not finalize within the timeout window.');
  }

  const execResult = receipt.txExecutionResultName;
  if (execResult !== ExecutionResult.FINISHED_WITH_RETURN) {
    let debugTrace = null;
    try {
      debugTrace = await client.debugTraceTransaction({ hash: txHash, round: 0 });
    } catch {
      // Best effort only.
    }
    const error = new Error(
      `Contract execution failed: ${execResult || 'unknown'}`
    );
    error.name = 'ContractExecutionError';
    error.meta = { txHash, receipt, debugTrace };
    throw error;
  }

  onStatus?.('Reading result…');

  const rawScore = await client.readContract({
    address: CONTRACT_ADDRESS,
    abi: ABI,
    functionName: 'get_score',
    args: [repoUrl]
  });

  const details = await getDetails(accountAddress, repoUrl);

  return {
    txHash,
    receipt,
    score: Number(rawScore),
    details
  };
}

export async function getCachedScore(accountAddress, repoUrl) {
  const client = buildGenLayerClient(accountAddress);

  const rawScore = await client.readContract({
    address: CONTRACT_ADDRESS,
    abi: ABI,
    functionName: 'get_score',
    args: [repoUrl]
  });

  const details = await getDetails(accountAddress, repoUrl);

  return {
    score: Number(rawScore),
    details
  };
}

export async function getDetails(accountAddress, repoUrl) {
  const client = buildGenLayerClient(accountAddress);

  const raw = await client.readContract({
    address: CONTRACT_ADDRESS,
    abi: ABI,
    functionName: 'get_details',
    args: [repoUrl]
  });

  try {
    return JSON.parse(String(raw || '{}'));
  } catch {
    return { parse_error: true, raw: String(raw || '') };
  }
}
