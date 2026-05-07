export const CONTRACT_ADDRESS = import.meta.env.VITE_CONTRACT_ADDRESS;
export const CHAIN_ID = Number(import.meta.env.VITE_CHAIN_ID);
export const CHAIN_ID_HEX = '0xF22F';
export const RPC_URL = 'http://127.0.0.1:4000/api';
export const NETWORK_NAME = 'GenLayer Studio';
export const TX_POLL_INTERVAL = 3000;
export const TX_POLL_RETRIES = 200;

export const ABI = [
  {
    name: 'analyze_repo',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [{ name: 'repo_url', type: 'string' }],
    outputs: [{ name: '', type: 'int256' }]
  },
  {
    name: 'get_score',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'repo_url', type: 'string' }],
    outputs: [{ name: '', type: 'int256' }]
  }
];
