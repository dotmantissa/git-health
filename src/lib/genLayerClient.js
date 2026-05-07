import { createClient } from 'genlayer-js';
import { studionet } from 'genlayer-js/chains';
import { TransactionStatus } from 'genlayer-js/types';
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
    interval: TX_POLL_INTERVAL
  });

  if (!receipt) {
    throw new Error('Transaction did not finalize within the timeout window.');
  }

  onStatus?.('Reading result…');

  const rawScore = await client.readContract({
    address: CONTRACT_ADDRESS,
    abi: ABI,
    functionName: 'get_score',
    args: [repoUrl]
  });

  return Number(rawScore);
}

export async function getCachedScore(accountAddress, repoUrl) {
  const client = buildGenLayerClient(accountAddress);

  const rawScore = await client.readContract({
    address: CONTRACT_ADDRESS,
    abi: ABI,
    functionName: 'get_score',
    args: [repoUrl]
  });

  return Number(rawScore);
}
