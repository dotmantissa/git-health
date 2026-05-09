const ENV_CONTRACT_ADDRESS = import.meta.env.VITE_CONTRACT_ADDRESS;
const ZERO_ADDRESS = '0x0000000000000000000000000000000000000000';
const DEFAULT_CONTRACT_ADDRESS = '0x3fBeCf6f135266997fAa819721f25cCeE9D144A7';

export const CONTRACT_ADDRESS =
  ENV_CONTRACT_ADDRESS && ENV_CONTRACT_ADDRESS !== ZERO_ADDRESS
    ? ENV_CONTRACT_ADDRESS
    : DEFAULT_CONTRACT_ADDRESS;
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
  },
  {
    name: 'get_details',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'repo_url', type: 'string' }],
    outputs: [{ name: '', type: 'string' }]
  }
];
