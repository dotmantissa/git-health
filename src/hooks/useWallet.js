import { useCallback, useEffect, useState } from 'react';
import { JsonRpcProvider } from 'ethers';
import { CHAIN_ID, RPC_URL } from '../constants';

const RPC_SESSION_KEY = 'githealth_rpc_connected';

export function useWallet() {
  const [provider, setProvider] = useState(null);
  const [signer, setSigner] = useState(null);
  const [address, setAddress] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [wrongNetwork, setWrongNetwork] = useState(false);
  const [chainId, setChainId] = useState(null);
  const [walletError, setWalletError] = useState('');

  const clearError = useCallback(() => {
    setWalletError('');
  }, []);

  const disconnect = useCallback(() => {
    localStorage.removeItem(RPC_SESSION_KEY);
    setProvider(null);
    setSigner(null);
    setAddress(null);
    setIsConnected(false);
    setWrongNetwork(false);
    setChainId(null);
    setWalletError('');
  }, []);

  const connectWithMode = useCallback(async (silent = false) => {
    clearError();

    try {
      const rpcProvider = new JsonRpcProvider(RPC_URL);
      const network = await rpcProvider.getNetwork();
      const currentChainId = Number(network.chainId);

      setProvider(rpcProvider);
      setChainId(currentChainId);

      if (currentChainId !== CHAIN_ID) {
        setWrongNetwork(true);
        setIsConnected(false);
        if (!silent) {
          setWalletError('Wrong network. RPC must point to GenLayer Studio (Chain ID 61999).');
        }
        return;
      }

      const accounts = await rpcProvider.send('eth_accounts', []);
      if (!accounts || accounts.length === 0) {
        setWrongNetwork(false);
        setIsConnected(false);
        setSigner(null);
        setAddress(null);
        if (!silent) {
          setWalletError('No RPC account available for signing. Start GenLayer Studio with an unlocked account.');
        }
        return;
      }

      const rpcSigner = await rpcProvider.getSigner(accounts[0]);
      const signerAddress = await rpcSigner.getAddress();

      setSigner(rpcSigner);
      setAddress(signerAddress);
      setWrongNetwork(false);
      setIsConnected(true);
      localStorage.setItem(RPC_SESSION_KEY, '1');
    } catch (error) {
      setIsConnected(false);
      setWrongNetwork(false);
      setSigner(null);
      setAddress(null);
      if (!silent) {
        setWalletError(error?.message || 'RPC connection failed — is GenLayer Studio running?');
      }
    }
  }, [clearError]);

  const connect = useCallback(async () => {
    await connectWithMode(false);
  }, [connectWithMode]);

  const switchToGenLayer = useCallback(async () => {
    await connectWithMode(false);
  }, [connectWithMode]);

  useEffect(() => {
    const shouldRestore = localStorage.getItem(RPC_SESSION_KEY) === '1';
    if (shouldRestore) {
      connectWithMode(true);
    }
  }, [connectWithMode]);

  return {
    provider,
    signer,
    address,
    isConnected,
    wrongNetwork,
    chainId,
    walletError,
    connect,
    disconnect,
    switchToGenLayer,
    clearError
  };
}
