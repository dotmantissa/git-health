export const CHAIN_ID = 61999;
export const CHAIN_ID_HEX = '0xF22F';
export const RPC_URL = 'http://localhost:4000/api';
export const NETWORK_NAME = 'GenLayer Studio';

export const CONTRACT_ADDRESS = '0x4A80762ebE1BC926b1Bee3eB9e388ae55f4Cf0Ee';

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
